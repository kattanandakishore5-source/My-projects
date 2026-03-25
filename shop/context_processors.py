from .models import Cart

def global_cart(request):
    if not request.session.session_key:
        return {'global_cart_count': 0}
    try:
        cart = Cart.objects.get(session_key=request.session.session_key)
        return {'global_cart_count': cart.items.count()}
    except Cart.DoesNotExist:
        return {'global_cart_count': 0}