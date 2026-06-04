from .models import Cart


def global_cart(request):
    if not request.session.session_key:
        return {'global_cart_count': 0}

    # Optimized: Removed try/except for a faster database query evaluation
    cart = Cart.objects.filter(session_key=request.session.session_key).first()

    return {'global_cart_count': cart.items.count() if cart else 0}