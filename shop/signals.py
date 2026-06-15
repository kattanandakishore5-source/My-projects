from django.db.models import Avg
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.utils import timezone

from .models import Product, ProductReview


@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
def invalidate_product_cache(sender, instance, **kwargs):
    """Invalidate the cached product object whenever a Product is saved or deleted."""
    cache.delete(f'product_{instance.id}')


@receiver(pre_save, sender=Product)
def track_product_stock_pre_save(sender, instance, **kwargs):
    """Store the current stock level before save to detect changes."""
    if instance.id:
        try:
            old_product = Product.objects.get(id=instance.id)
            instance._old_stock = old_product.stock
        except Product.DoesNotExist:
            instance._old_stock = None
    else:
        instance._old_stock = None


@receiver(post_save, sender=Product)
def track_product_stock_post_save(sender, instance, created, **kwargs):
    """
    Detect stock changes (sales, restocks, new products) and send instant
    notifications & alerts as appropriate.
    """
    old_stock = getattr(instance, '_old_stock', None)
    new_stock = instance.stock

    # If stock hasn't changed, nothing to do
    if old_stock == new_stock:
        return

    from shop.tasks import send_telegram_message

    # 1. Detect Sale or Restock / Purchase
    now = timezone.now().astimezone(timezone.get_current_timezone())
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    if old_stock is None:
        # Newly created product with stock > 0
        if new_stock > 0:
            msg = (
                f"🆕 <b>PRODUCT ADDED</b> 🆕\n\n"
                f"Product: <b>{instance.product_name}</b>\n"
                f"Initial Stock: <b>{new_stock}</b>\n"
                f"Date: <b>{date_str}</b>\n"
                f"Time: <b>{time_str}</b>"
            )
            send_telegram_message.delay(msg)
    else:
        diff = abs(new_stock - old_stock)
        if new_stock > old_stock:
            # Restock / Purchased by store
            msg = (
                f"📦 <b>PRODUCT RESTOCKED / PURCHASED</b> 📦\n\n"
                f"Product: <b>{instance.product_name}</b>\n"
                f"Quantity Added: <b>{diff}</b>\n"
                f"Remaining Stock: <b>{new_stock}</b>\n"
                f"Date: <b>{date_str}</b>\n"
                f"Time: <b>{time_str}</b>"
            )
            send_telegram_message.delay(msg)

            # Reset any low-stock / out-of-stock alert flags in cache if stock is now sufficient
            if new_stock > instance.low_stock_threshold:
                cache.delete(f"low_stock_alert_sent_{instance.id}")
                cache.delete(f"out_of_stock_alert_sent_{instance.id}")
            elif new_stock > 0:
                cache.delete(f"out_of_stock_alert_sent_{instance.id}")
        else:
            # Sale to customer
            msg = (
                f"🛍️ <b>PRODUCT SOLD</b> 🛍️\n\n"
                f"Product: <b>{instance.product_name}</b>\n"
                f"Quantity Sold: <b>{diff}</b>\n"
                f"Remaining Stock: <b>{new_stock}</b>\n"
                f"Date: <b>{date_str}</b>\n"
                f"Time: <b>{time_str}</b>"
            )
            send_telegram_message.delay(msg)

    # 2. Check for Low Stock / Out of Stock alerts
    if new_stock == 0:
        out_of_stock_cache_key = f"out_of_stock_alert_sent_{instance.id}"
        if not cache.get(out_of_stock_cache_key):
            alert_msg = (
                f"🚨 <b>OUT OF STOCK ALERT</b> 🚨\n\n"
                f"The product <b>{instance.product_name}</b> is now out of stock!\n"
                f"Please restock immediately."
            )
            send_telegram_message.delay(alert_msg)
            cache.set(out_of_stock_cache_key, True, timeout=86400)  # 24 hour cooldown
    elif new_stock <= instance.low_stock_threshold:
        low_stock_cache_key = f"low_stock_alert_sent_{instance.id}"
        if not cache.get(low_stock_cache_key):
            recommended = max(0, max(10, instance.low_stock_threshold * 5) - new_stock)
            alert_msg = (
                f"⚠️ <b>LOW STOCK ALERT</b> ⚠️\n\n"
                f"Product: <b>{instance.product_name}</b>\n"
                f"Current Stock: <b>{new_stock}</b>\n"
                f"Minimum Threshold: <b>{instance.low_stock_threshold}</b>\n"
                f"Recommended Restock: <b>{recommended}</b>"
            )
            send_telegram_message.delay(alert_msg)
            cache.set(low_stock_cache_key, True, timeout=86400)  # 24 hour cooldown


@receiver(post_save, sender=ProductReview)
@receiver(post_delete, sender=ProductReview)
def update_product_rating_stats(sender, instance, **kwargs):
    """
    Recalculate and update a Product's average_rating and review_count
    whenever a ProductReview is created, updated, or deleted.
    """
    product = instance.product
    reviews = product.reviews.all()
    count = reviews.count()
    if count > 0:
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0.0
    else:
        avg_rating = 0.0

    product.average_rating = avg_rating
    product.review_count = count
    product.save(update_fields=['average_rating', 'review_count'])

    # Also invalidate the product cache so detail pages reflect new ratings
    cache.delete(f'product_{product.id}')

