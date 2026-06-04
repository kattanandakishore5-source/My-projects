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

MERCHANT_KEY = 'Your-Merchant-Key-Here'


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
    all_products = Product.objects.filter(stock__gt=0).order_by('category')

    for cat, prod_group in groupby(all_products, key=attrgetter('category')):
        prod = list(prod_group)
        for p in prod:
            p.cart_qty = cart_items_dict.get(p.id, 0)
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

    # Optimized: Removed Python-side loop filtering. Used DB-level ORM lookups.
    if len(query) >= 4:
        all_products = Product.objects.filter(
            Q(product_name__icontains=query) |
            Q(desc__icontains=query) |
            Q(category__icontains=query) |
            Q(subcategory__icontains=query),
            stock__gt=0
        ).order_by('category')

        for cat, prod_group in groupby(all_products, key=attrgetter('category')):
            prod = list(prod_group)
            for p in prod:
                p.cart_qty = cart_items_dict.get(p.id, 0)

            n = len(prod)
            nSlides = n // 4 + ceil((n / 4) - (n // 4))
            if n != 0:
                allProds.append([prod, range(1, nSlides), nSlides, n > 4])

    params = {'allProds': allProds, "msg": ""}
    if len(allProds) == 0 or len(query) < 4:
        params = {'msg': "Please make sure to enter a relevant search query of at least 4 characters"}

    return render(request, 'shop/search.html', params)


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

    recently_viewed = Product.objects.filter(id__in=recently_viewed_ids).exclude(id=myid)
    for rv in recently_viewed:
        rv.cart_qty = cart_items_dict.get(rv.id, 0)

    recommendations = Product.objects.filter(category=product.category, stock__gt=0).exclude(id=myid)[:4]
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
def handlerequest(request):
    try:
        from PayTm import Checksum
    except ModuleNotFoundError:
        return HttpResponse("PayTM dependencies are not installed on this server.")
    form = request.POST
    response_dict = {}
    for i in form.keys():
        response_dict[i] = form[i]
        if i == 'CHECKSUMHASH':
            checksum = form[i]
    verify = Checksum.verify_checksum(response_dict, MERCHANT_KEY, checksum)
    if verify:
        if response_dict['RESPCODE'] == '01':
            print('order successful')
        else:
            print('order was not successful because' + response_dict['RESPMSG'])
    return render(request, 'shop/paymentstatus.html', {'response': response_dict})


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
            return render(request, 'shop/partials/button_actions.html',
                          {'i': product, 'cart_items': cart_items, 'is_htmx': True, 'user': request.user})

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
            from PayTm import Checksum
            param_dict = {
                'MID': 'Your-Merchant-Id-Here', 'ORDER_ID': str(order.order_id), 'TXN_AMOUNT': str(amount),
                'CUST_ID': email, 'INDUSTRY_TYPE_ID': 'Retail', 'WEBSITE': 'WEBSTAGING', 'CHANNEL_ID': 'WEB',
                'CALLBACK_URL': 'http://127.0.0.1:8000/shop/handlerequest/',
            }
            param_dict['CHECKSUMHASH'] = Checksum.generate_checksum(param_dict, MERCHANT_KEY)
            return render(request, 'shop/paytm.html', {'param_dict': param_dict})
        except ModuleNotFoundError:
            return render(request, 'shop/checkout.html', {'thank': True, 'id': order.order_id})

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
        else:
            Wishlist.objects.create(user=request.user, product=product)

        if request.headers.get('HX-Request'):
            current_url = request.headers.get('Hx-Current-Url', '')
            if '/wishlist/' in current_url:
                return wishlist_view(request)

            cart = _get_or_create_cart(request)
            try:
                cart_item = CartItem.objects.get(cart=cart, product=product)
                product.cart_qty = cart_item.quantity
            except CartItem.DoesNotExist:
                product.cart_qty = 0

            cart_items = cart.items.count()
            return render(request, 'shop/partials/button_actions.html', {
                'i': product,
                'cart_items': cart_items,
                'is_htmx': True,
                'user': request.user
            })

    referer = request.META.get('HTTP_REFERER', '/')
    return redirect(referer.split('#')[0])