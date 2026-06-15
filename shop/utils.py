"""
Shared helper functions for the shop app.

Provides DRY utilities used across multiple views to avoid code duplication.
"""

from math import ceil
from itertools import groupby
from operator import attrgetter

from .models import Coupon


def calculate_cart_total(cart, session_coupon_id):
    """
    Calculate the cart total, applying any active coupon discount.

    Args:
        cart: Cart model instance.
        session_coupon_id: The coupon ID from request.session.get('coupon_id').

    Returns:
        Tuple of (subtotal, discount_amount, total, coupon_obj).
        coupon_obj is None if no valid coupon is applied.
    """
    items = cart.items.select_related('product').all()
    subtotal = sum(item.product.price * item.quantity for item in items)
    discount_amount = 0
    coupon = None

    if session_coupon_id:
        try:
            coupon = Coupon.objects.get(id=session_coupon_id, active=True)
            if coupon.discount_type == 'Percentage':
                discount_amount = int((coupon.discount_value / 100) * subtotal)
            elif coupon.discount_type == 'Flat':
                discount_amount = coupon.discount_value
            if discount_amount > subtotal:
                discount_amount = subtotal
        except Coupon.DoesNotExist:
            coupon = None

    total = subtotal - discount_amount
    return subtotal, discount_amount, total, coupon


def build_product_carousel(products, cart_items_dict, user_wishlist_ids):
    """
    Group products by category and build carousel slide data.

    Args:
        products: QuerySet of Product objects, ordered by category.
        cart_items_dict: Dict mapping product_id → quantity in cart.
        user_wishlist_ids: Set of product IDs in the user's wishlist.

    Returns:
        List of [products_list, slide_range, num_slides, has_multiple_slides]
        entries, one per category.
    """
    all_prods = []
    for cat, prod_group in groupby(products, key=attrgetter('category')):
        prod = list(prod_group)
        for p in prod:
            p.cart_qty = cart_items_dict.get(p.id, 0)
            p.in_wishlist = p.id in user_wishlist_ids
        n = len(prod)
        n_slides = ceil(n / 4)
        if n != 0:
            all_prods.append([prod, range(1, n_slides), n_slides, n > 4])
    return all_prods
