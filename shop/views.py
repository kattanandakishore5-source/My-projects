from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Contact, Orders, OrderUpdate, Cart, CartItem, Coupon, Wishlist, ProductReview
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from math import ceil
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils import timezone
from .forms import CouponApplyForm, ReviewForm
from django.contrib.auth.decorators import login_required
from django.conf import settings
import razorpay


def _get_or_create_cart(request):
    if not request.session.session_key:
        request.session.create()
    cart, created = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart


def index(request):
    cart = _get_or_create_cart(request)
    cart_items_dict = {item.product_id: item.quantity for item in cart.items.all()}

    from itertools import groupby
    from operator import attrgetter

    allProds = []
    all_products = Product.objects.filter(stock__gt=0).prefetch_related('reviews').order_by('category')

    user_wishlist_ids = set()
    if request.user.is_authenticated:
        user_wishlist_ids = set(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    for cat, prod_group in groupby(all_products, key=attrgetter('category')):
        prod = list(prod_group)
        for p in prod:
            p.cart_qty = cart_items_dict.get(p.id, 0)
            p.in_wishlist = p.id in user_wishlist_ids
        n = len(prod)
        nSlides = n // 4 + ceil((n / 4) - (n // 4))
        if n != 0:
            allProds.append([prod, range(1, nSlides), nSlides, n > 4])

    params = {'allProds': allProds}
    return render(request, 'shop/index.html', params)


def search(request):
    query = request.GET.get('search', '').strip()
    allProds = []

    cart = _get_or_create_cart(request)
    cart_items_dict = {item.product_id: item.quantity for item in cart.items.all()}

    from itertools import groupby
    from operator import attrgetter

    user_wishlist_ids = set()
    if request.user.is_authenticated:
        user_wishlist_ids = set(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    # Optimized: Removed Python-side loop filtering. Used DB-level ORM lookups.
    if len(query) >= 4:
        all_products = Product.objects.filter(
            Q(product_name__icontains=query) |
            Q(desc__icontains=query) |
            Q(category__icontains=query) |
            Q(subcategory__icontains=query),
            stock__gt=0
        ).prefetch_related('reviews').order_by('category')

        for cat, prod_group in groupby(all_products, key=attrgetter('category')):
            prod = list(prod_group)
            for p in prod:
                p.cart_qty = cart_items_dict.get(p.id, 0)
                p.in_wishlist = p.id in user_wishlist_ids

            n = len(prod)
            nSlides = n // 4 + ceil((n / 4) - (n // 4))
            if n != 0:
                allProds.append([prod, range(1, nSlides), nSlides, n > 4])

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
        contact = Contact(name=name, email=email, phone=phone, desc=desc)
        contact.save()
        thank = True
    return render(request, 'shop/contact.html', {'thank': thank})


def tracker(request):
    if request.method == "POST":
        orderId = request.POST.get('orderId', '')
        email = request.POST.get('email', '')
        try:
            order = Orders.objects.filter(order_id=orderId, email=email)
            if len(order) > 0:
                update = OrderUpdate.objects.filter(order_id=orderId)
                updates = [{'text': item.update_desc, 'time': item.timestamp} for item in update]
                response = json.dumps({"status": "success", "updates": updates, "itemsJson": order[0].items_json},
                                      default=str)
                return HttpResponse(response)
            else:
                return HttpResponse('{"status":"noitem"}')
        except Exception as e:
            return HttpResponse('{"status":"error"}')
    return render(request, 'shop/tracker.html')


def productView(request, myid):
    product = get_object_or_404(Product, id=myid)
    review_list = product.reviews.all().order_by('-created_at')

    cart = _get_or_create_cart(request)
    cart_items_dict = {item.product_id: item.quantity for item in cart.items.all()}

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

    recommendations = Product.objects.filter(category=product.category, stock__gt=0).prefetch_related('reviews').exclude(id=myid)[:4]
    for rec in recommendations:
        rec.cart_qty = cart_items_dict.get(rec.id, 0)

    paginator = Paginator(review_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == "POST":
        if not request.user.is_authenticated: return redirect('login')
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
            
            # Payment signature is verified
            order = Orders.objects.filter(razorpay_order_id=razorpay_order_id).first()
            if order:
                order.payment_status = 'PAID'
                order.save()
                OrderUpdate(order_id=order.order_id, update_desc="The payment was successful and order is confirmed").save()
            return render(request, 'shop/payment_status.html', {'status': 'success', 'order_id': order.order_id if order else ''})
            
        except razorpay.errors.SignatureVerificationError:
            order = Orders.objects.filter(razorpay_order_id=razorpay_order_id).first()
            if order:
                order.payment_status = 'FAILED'
                order.save()
                OrderUpdate(order_id=order.order_id, update_desc="Payment signature verification failed").save()
            return render(request, 'shop/payment_status.html', {'status': 'failed', 'order_id': order.order_id if order else ''})
        except Exception as e:
            return HttpResponse(f"Error: {str(e)}")
    
    return HttpResponse("Invalid Request")


def add_to_cart(request, product_id):
    if request.method == 'POST':
        cart = _get_or_create_cart(request)
        product = get_object_or_404(Product, id=product_id)

        if product.stock > 0:
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            if not created:
                if cart_item.quantity < product.stock:
                    cart_item.quantity += 1
                    cart_item.save()

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

    for item in cart.items.select_related('product').all():
        if item.product.stock < item.quantity:
            item.delete()

    subtotal = sum(item.product.price * item.quantity for item in cart.items.select_related('product').all())
    coupon_id = request.session.get('coupon_id')
    discount_amount = 0
    coupon = None
    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id, active=True)
            if coupon.discount_type == 'Percentage':
                discount_amount = int((coupon.discount_value / 100) * subtotal)
            elif coupon.discount_type == 'Flat':
                discount_amount = coupon.discount_value
            if discount_amount > subtotal:
                discount_amount = subtotal
        except Coupon.DoesNotExist:
            request.session['coupon_id'] = None

    total = subtotal - discount_amount
    context = {'cart': cart, 'subtotal': subtotal, 'discount': discount_amount, 'total': total, 'coupon': coupon}
    return render(request, 'shop/cart.html', context)


def update_cart_item(request, product_id, action):
    cart = _get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, product_id=product_id, cart=cart)
    product = cart_item.product

    if action == 'increment':
        if cart_item.quantity < product.stock:
            cart_item.quantity += 1
            cart_item.save()
    elif action == 'decrement':
        cart_item.quantity -= 1
        if cart_item.quantity <= 0:
            cart_item.delete()
            cart_item.quantity = 0
        else:
            cart_item.save()

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


def remove_from_cart(request, product_id):
    cart = _get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, product_id=product_id, cart=cart)
    cart_item.delete()
    # Fixed potential issue if HTTP_REFERER is missing
    return redirect(request.META.get('HTTP_REFERER', 'CartDetail'))


def coupon_apply(request):
    now = timezone.now().date()
    if request.method == "POST":
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


def checkout(request):
    if request.method == "POST":
        items_json = request.POST.get('itemsJson', '')
        name = request.POST.get('name', '')
        amount = request.POST.get('amount', '')
        email = request.POST.get('email', '')
        address = request.POST.get('address1', '') + " " + request.POST.get('address2', '')
        city = request.POST.get('city', '')
        state = request.POST.get('state', '')
        zip_code = request.POST.get('zip_code', '')
        phone = request.POST.get('phone', '')

        current_user = request.user if request.user.is_authenticated else None
        cart = _get_or_create_cart(request)

        try:
            with transaction.atomic():
                product_ids = [item.product.id for item in cart.items.select_related('product').all()]
                locked_products = Product.objects.select_for_update().filter(id__in=product_ids)
                stock_dict = {p.id: p for p in locked_products}

                for item in cart.items.select_related('product').all():
                    p = stock_dict.get(item.product.id)
                    if not p or p.stock < item.quantity:
                        return HttpResponse(f"Sorry, '{item.product.product_name}' just went out of stock!")

                for item in cart.items.select_related('product').all():
                    p = stock_dict[item.product.id]
                    p.stock -= item.quantity
                    p.save()

                order = Orders(items_json=items_json, name=name, email=email, address=address, city=city, state=state,
                               zip_code=zip_code, phone=phone, amount=amount, user=current_user)
                order.save()
                OrderUpdate(order_id=order.order_id, update_desc="The order has been placed").save()

                request.session['coupon_id'] = None
                cart.items.all().delete()

        except Exception as e:
            return HttpResponse("An error occurred during checkout. Please try again.")

        try:
            amount_in_paise = int(float(amount) * 100)
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            razorpay_order = client.order.create({
                'amount': amount_in_paise,
                'currency': 'INR',
                'payment_capture': '1'
            })
            order.razorpay_order_id = razorpay_order['id']
            order.save()
            
            # The URL host and port should ideally come from request, but we will use the host from the request
            host = request.get_host()
            scheme = request.is_secure() and "https" or "http"
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
            return HttpResponse(f"Error creating Razorpay order: {str(e)}")

    cart = _get_or_create_cart(request)
    subtotal = sum(item.product.price * item.quantity for item in cart.items.select_related('product').all())
    coupon_id = request.session.get('coupon_id')
    discount_amount = 0
    coupon = None

    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id, active=True)
            if coupon.discount_type == 'Percentage':
                discount_amount = int((coupon.discount_value / 100) * subtotal)
            elif coupon.discount_type == 'Flat':
                discount_amount = coupon.discount_value
            if discount_amount > subtotal:
                discount_amount = subtotal
        except Coupon.DoesNotExist:
            request.session['coupon_id'] = None

    total = subtotal - discount_amount
    context = {'cart': cart, 'subtotal': subtotal, 'discount': discount_amount, 'total': total, 'coupon': coupon}
    return render(request, 'shop/checkout.html', context)


@login_required
def my_orders(request):
    orders = Orders.objects.filter(user=request.user).order_by('-order_id')
    return render(request, 'shop/my_orders.html', {'orders': orders})


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
            product.in_wishlist = False
        else:
            Wishlist.objects.create(user=request.user, product=product)
            msg = f"Added {product.product_name} to wishlist"
            product.in_wishlist = True

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