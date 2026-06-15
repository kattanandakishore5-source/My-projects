import json
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django.core.cache import cache
import razorpay

from .models import Product, Contact, Orders, OrderUpdate, Cart, CartItem, Coupon, Wishlist
from .forms import ReviewForm
from .utils import calculate_cart_total, build_product_carousel
from shop.tasks import send_order_confirmation_email

logger = logging.getLogger(__name__)


def _get_or_create_cart(request):
    if not request.session.session_key:
        request.session.create()
    cart, created = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart


def _get_cart_items_dict(cart):
    """Build a product_id -> quantity mapping for the given cart."""
    return {item.product_id: item.quantity for item in cart.items.all()}


def _get_user_wishlist_ids(user):
    """Return the set of product IDs in the user's wishlist."""
    if user.is_authenticated:
        return set(Wishlist.objects.filter(user=user).values_list('product_id', flat=True))
    return set()


def _search_products(query):
    """
    Search products using PostgreSQL Full-Text Search when available,
    with an automatic fallback to __icontains for SQLite.
    """
    from django.db import connection

    base_qs = Product.objects.filter(stock__gt=0, is_active=True)

    if connection.vendor == 'postgresql':
        from django.contrib.postgres.search import SearchVector, SearchQuery
        search_vector = SearchVector('product_name', 'desc', 'category', 'subcategory')
        search_query = SearchQuery(query)
        return base_qs.annotate(search=search_vector).filter(
            search=search_query
        ).prefetch_related('reviews').order_by('category')
    else:
        # SQLite fallback
        from django.db.models import Q
        return base_qs.filter(
            Q(product_name__icontains=query) |
            Q(desc__icontains=query) |
            Q(category__icontains=query) |
            Q(subcategory__icontains=query),
        ).prefetch_related('reviews').order_by('category')


# ─── Public Views ─────────────────────────────────────────────


@vary_on_cookie
@cache_page(60 * 5)
def index(request):
    cart = _get_or_create_cart(request)
    cart_items_dict = _get_cart_items_dict(cart)
    user_wishlist_ids = _get_user_wishlist_ids(request.user)

    all_products = Product.objects.filter(
        stock__gt=0, is_active=True,
    ).prefetch_related('reviews').order_by('category')

    allProds = build_product_carousel(all_products, cart_items_dict, user_wishlist_ids)

    return render(request, 'shop/index.html', {'allProds': allProds})


def search(request):
    query = request.GET.get('search', '').strip()
    allProds = []

    cart = _get_or_create_cart(request)
    cart_items_dict = _get_cart_items_dict(cart)
    user_wishlist_ids = _get_user_wishlist_ids(request.user)

    if len(query) >= 4:
        all_products = _search_products(query)
        allProds = build_product_carousel(all_products, cart_items_dict, user_wishlist_ids)

    params = {'allProds': allProds, "msg": ""}
    if len(allProds) == 0 or len(query) < 4:
        params = {'msg': "Please make sure to enter a relevant search query of at least 4 characters"}

    response = render(request, 'shop/search.html', params)
    if params['msg'] and request.headers.get('HX-Request'):
        response['HX-Trigger'] = json.dumps({"showError": params['msg']})
    return response


def about(request):
    return render(request, 'shop/about.html')


def contact(request):
    thank = False
    if request.method == "POST":
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        desc = request.POST.get('desc', '')
        contact_obj = Contact(name=name, email=email, phone=phone, desc=desc)
        contact_obj.save()
        thank = True
    return render(request, 'shop/contact.html', {'thank': thank})


def tracker(request):
    if request.method == "POST":
        raw_order_id = request.POST.get('orderId', '')
        email = request.POST.get('email', '')
        try:
            order_id = int(raw_order_id)
        except (ValueError, TypeError):
            return JsonResponse({"status": "error", "message": "Invalid Order ID"})
        try:
            order = Orders.objects.filter(order_id=order_id, email=email)
            if len(order) > 0:
                update = OrderUpdate.objects.filter(order_id=order_id)
                updates = [{'text': item.update_desc, 'time': item.timestamp} for item in update]
                response = json.dumps(
                    {"status": "success", "updates": updates, "itemsJson": order[0].items_json},
                    default=str,
                )
                return HttpResponse(response)
            else:
                return JsonResponse({"status": "noitem"})
        except Exception as e:
            logger.exception("Error in tracker: %s", str(e))
            return JsonResponse({"status": "error"})
    return render(request, 'shop/tracker.html')


def productView(request, myid):
    cache_key = f'product_{myid}'
    product = cache.get(cache_key)
    if product is None:
        product = get_object_or_404(Product, id=myid)
        cache.set(cache_key, product, 60 * 10)
    review_list = product.reviews.all().order_by('-created_at')

    cart = _get_or_create_cart(request)
    cart_items_dict = _get_cart_items_dict(cart)

    product.cart_qty = cart_items_dict.get(product.id, 0)

    if 'recently_viewed' not in request.session:
        request.session['recently_viewed'] = []

    recently_viewed_ids = request.session['recently_viewed']

    if myid in recently_viewed_ids:
        recently_viewed_ids.remove(myid)
    recently_viewed_ids.insert(0, myid)

    request.session['recently_viewed'] = recently_viewed_ids[:6]
    request.session.modified = True

    recently_viewed = Product.objects.filter(id__in=recently_viewed_ids).prefetch_related('reviews').exclude(id=myid)
    for rv in recently_viewed:
        rv.cart_qty = cart_items_dict.get(rv.id, 0)

    recommendations = Product.objects.filter(
        category=product.category, stock__gt=0, is_active=True,
    ).prefetch_related('reviews').exclude(id=myid)[:4]
    for rec in recommendations:
        rec.cart_qty = cart_items_dict.get(rec.id, 0)

    paginator = Paginator(review_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect('login')
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = form.save(commit=False)
            review.product, review.user = product, request.user
            review.save()
            return redirect(f"/shop/products/{myid}")
    else:
        form = ReviewForm()

    return render(request, 'shop/prodView.html', {
        'product': product,
        'page_obj': page_obj,
        'form': form,
        'recommendations': recommendations,
        'recently_viewed': recently_viewed,
        'cart_items': cart.items.count()
    })


# ─── Payment ──────────────────────────────────────────────────


@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        data = request.POST
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })

            order = Orders.objects.filter(razorpay_order_id=razorpay_order_id).first()
            if order:
                order.payment_status = 'PAID'
                order.save()
                OrderUpdate(order_id=order.order_id, update_desc="The payment was successful and order is confirmed").save()
                send_order_confirmation_email.delay(order.order_id)
            return render(request, 'shop/payment_status.html', {'status': 'success', 'order_id': order.order_id if order else ''})

        except razorpay.errors.SignatureVerificationError:
            order = Orders.objects.filter(razorpay_order_id=razorpay_order_id).first()
            if order:
                order.payment_status = 'FAILED'
                order.save()
                OrderUpdate(order_id=order.order_id, update_desc="Payment signature verification failed").save()
            return render(request, 'shop/payment_status.html', {'status': 'failed', 'order_id': order.order_id if order else ''})
        except Exception as e:
            logger.exception("Error in payment_success: %s", str(e))
            return HttpResponse("An error occurred while processing your payment. Please try again.")

    return HttpResponse("Invalid Request")


# ─── Cart ─────────────────────────────────────────────────────


@require_POST
def add_to_cart(request, product_id):
    cart = _get_or_create_cart(request)
    product = get_object_or_404(Product, id=product_id)

    if product.stock > 0:
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            if cart_item.quantity < product.stock:
                CartItem.objects.filter(pk=cart_item.pk).update(quantity=F('quantity') + 1)
                cart_item.refresh_from_db()

    # JSON response for Vanilla JS fetch()
    if 'application/json' in request.headers.get('Accept', ''):
        try:
            cart_item = CartItem.objects.get(cart=cart, product=product)
            qty = cart_item.quantity
        except CartItem.DoesNotExist:
            qty = 0
        return JsonResponse({
            'status': 'ok',
            'cart_qty': qty,
            'cart_count': cart.items.count(),
            'message': f'Added {product.product_name} to cart'
        })

    # Legacy HTMX fallback
    if request.headers.get('HX-Request'):
        current_url = request.headers.get('Hx-Current-Url', '')
        if '/wishlist/' in current_url:
            return wishlist_view(request)

        try:
            cart_item = CartItem.objects.get(cart=cart, product=product)
            product.cart_qty = cart_item.quantity
        except CartItem.DoesNotExist:
            product.cart_qty = 0
        cart_items = cart.items.count()
        response = render(request, 'shop/partials/button_actions.html',
                      {'i': product, 'cart_items': cart_items, 'is_htmx': True, 'user': request.user})
        response['HX-Trigger'] = json.dumps({"showMessage": f"Added {product.product_name} to cart"})
        return response

    referer = request.META.get('HTTP_REFERER', '/')
    base_url = referer.split('#')[0]
    return redirect(f"{base_url}#namepr{product_id}")


def cart_detail(request):
    cart = _get_or_create_cart(request)

    # Atomic single-query cleanup for items exceeding available stock
    cart.items.filter(quantity__gt=F('product__stock')).delete()

    subtotal, discount_amount, total, coupon = calculate_cart_total(cart, request.session.get('coupon_id'))

    if coupon is None and request.session.get('coupon_id'):
        request.session['coupon_id'] = None

    context = {'cart': cart, 'subtotal': subtotal, 'discount': discount_amount, 'total': total, 'coupon': coupon}
    return render(request, 'shop/cart.html', context)


@require_POST
def update_cart_item(request, product_id, action):
    cart = _get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, product_id=product_id, cart=cart)
    product = cart_item.product

    if action == 'increment':
        if cart_item.quantity < product.stock:
            CartItem.objects.filter(pk=cart_item.pk).update(quantity=F('quantity') + 1)
            cart_item.refresh_from_db()
    elif action == 'decrement':
        CartItem.objects.filter(pk=cart_item.pk).update(quantity=F('quantity') - 1)
        cart_item.refresh_from_db()
        if cart_item.quantity <= 0:
            cart_item.delete()
            cart_item.quantity = 0

    # JSON response for Vanilla JS fetch()
    if 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({
            'status': 'ok',
            'cart_qty': cart_item.quantity,
            'cart_count': cart.items.count(),
            'message': 'Cart updated'
        })

    # Legacy HTMX fallback
    if request.headers.get('HX-Request'):
        current_url = request.headers.get('Hx-Current-Url', '')
        if '/cart/' in current_url:
            return cart_detail(request)

        product.cart_qty = cart_item.quantity
        cart_items = cart.items.count()
        return render(request, 'shop/partials/button_actions.html',
                      {'i': product, 'cart_items': cart_items, 'is_htmx': True, 'user': request.user})

    referer = request.META.get('HTTP_REFERER', '/')
    base_url = referer.split('#')[0]
    return redirect(f"{base_url}#namepr{product_id}")


@require_POST
def remove_from_cart(request, product_id):
    cart = _get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, product_id=product_id, cart=cart)
    cart_item.delete()
    return redirect(request.META.get('HTTP_REFERER', 'CartDetail'))


@require_POST
def coupon_apply(request):
    now = timezone.now().date()
    code = request.POST.get('code', '').strip()
    if not code:
        if 'coupon_id' in request.session:
            del request.session['coupon_id']
        return redirect('CartDetail')
    try:
        coupon = Coupon.objects.get(code__iexact=code, valid_from__lte=now, valid_to__gte=now, active=True)
        request.session['coupon_id'] = coupon.id
    except Coupon.DoesNotExist:
        if 'coupon_id' in request.session:
            del request.session['coupon_id']
    return redirect('CartDetail')


# ─── Checkout ─────────────────────────────────────────────────


@login_required
def checkout(request):
    if request.method == "POST":
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        address = request.POST.get('address1', '') + " " + request.POST.get('address2', '')
        city = request.POST.get('city', '')
        state = request.POST.get('state', '')
        zip_code = request.POST.get('zip_code', '')
        phone = request.POST.get('phone', '')

        current_user = request.user if request.user.is_authenticated else None
        cart = _get_or_create_cart(request)

        # Query once and list-ify to avoid N+1 and query redundancy in loops
        cart_items = list(cart.items.select_related('product').all())

        # Backend-calculated total (never trust client-side amount)
        subtotal, discount_amount, amount, _coupon = calculate_cart_total(
            cart, request.session.get('coupon_id')
        )

        # Build items_json as a proper dict for JSONField
        items_data = {
            str(item.product.id): {
                'name': item.product.product_name,
                'qty': item.quantity,
                'price': item.product.price,
            }
            for item in cart_items
        }

        try:
            with transaction.atomic():
                product_ids = [item.product.id for item in cart_items]
                locked_products = Product.objects.select_for_update().filter(id__in=product_ids)
                stock_dict = {p.id: p for p in locked_products}

                for item in cart_items:
                    p = stock_dict.get(item.product.id)
                    if not p or p.stock < item.quantity:
                        return HttpResponse(f"Sorry, '{item.product.product_name}' just went out of stock!")

                for item in cart_items:
                    p = stock_dict[item.product.id]
                    p.stock -= item.quantity
                    p.save()

                order = Orders(
                    items_json=items_data, name=name, email=email, address=address,
                    city=city, state=state, zip_code=zip_code, phone=phone,
                    amount=amount, user=current_user,
                )
                order.save()
                OrderUpdate(order_id=order.order_id, update_desc="The order has been placed").save()

                request.session['coupon_id'] = None
                cart.items.all().delete()

        except Exception as e:
            logger.exception("Error in checkout: %s", str(e))
            return HttpResponse("An error occurred during checkout. Please try again.")

        try:
            amount_in_paise = int(amount * 100)
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            razorpay_order = client.order.create({
                'amount': amount_in_paise,
                'currency': 'INR',
                'payment_capture': '1'
            })
            order.razorpay_order_id = razorpay_order['id']
            order.save()

            host = request.get_host()
            scheme = "https" if request.is_secure() else "http"
            callback_url = f"{scheme}://{host}/shop/payment-success/"

            context = {
                'order_id': order.order_id,
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
                'razorpay_amount': amount_in_paise,
                'currency': 'INR',
                'callback_url': callback_url,
                'name': name,
                'email': email,
                'phone': phone,
            }
            return render(request, 'shop/razorpay_checkout.html', context)
        except Exception as e:
            logger.exception("Error in checkout (Razorpay): %s", str(e))
            return HttpResponse("An error occurred while initiating payment. Please try again.")

    # GET — show checkout page
    cart = _get_or_create_cart(request)
    subtotal, discount_amount, total, coupon = calculate_cart_total(cart, request.session.get('coupon_id'))

    if coupon is None and request.session.get('coupon_id'):
        request.session['coupon_id'] = None

    context = {'cart': cart, 'subtotal': subtotal, 'discount': discount_amount, 'total': total, 'coupon': coupon}
    return render(request, 'shop/checkout.html', context)


# ─── Orders & Wishlist ────────────────────────────────────────


@login_required
def my_orders(request):
    orders = Orders.objects.filter(user=request.user).order_by('-order_id')
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'shop/my_orders.html', {'page_obj': page_obj})


@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    cart = _get_or_create_cart(request)
    return render(request, 'shop/wishlist.html', {'wishlist_items': wishlist_items, 'cart': cart})


@login_required
def toggle_wishlist(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()
        if wishlist_item:
            wishlist_item.delete()
            msg = f"Removed {product.product_name} from wishlist"
            in_wishlist = False
        else:
            Wishlist.objects.create(user=request.user, product=product)
            msg = f"Added {product.product_name} to wishlist"
            in_wishlist = True

        # JSON response for Vanilla JS fetch()
        if 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({
                'status': 'ok',
                'in_wishlist': in_wishlist,
                'message': msg
            })

        # Legacy HTMX fallback
        product.in_wishlist = in_wishlist
        if request.headers.get('HX-Request'):
            current_url = request.headers.get('Hx-Current-Url', '')
            if '/wishlist/' in current_url:
                response = wishlist_view(request)
                response['HX-Trigger'] = json.dumps({"showMessage": msg})
                return response

            response = render(request, 'shop/partials/wishlist_icon.html', {
                'i': product,
                'is_htmx': True,
                'user': request.user
            })
            response['HX-Trigger'] = json.dumps({"showMessage": msg})
            return response

    referer = request.META.get('HTTP_REFERER', '/')
    return redirect(referer.split('#')[0])