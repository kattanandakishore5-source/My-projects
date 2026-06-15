"""
Celery tasks for the shop app.

Provides:
  - Asynchronous order confirmation emails after successful payment.
  - Periodic low-stock monitoring with Telegram alerts.
  - Asynchronous Telegram message delivery.
"""

import logging
import requests
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import F
from decouple import config

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_confirmation_email(self, order_id):
    """
    Send an order confirmation email asynchronously.
    Idempotent: only sends if payment_status == 'PAID'.
    """
    from shop.models import Orders

    try:
        order = Orders.objects.get(order_id=order_id)
    except Orders.DoesNotExist:
        logger.error("Order #%s not found — cannot send confirmation email.", order_id)
        return

    if order.payment_status != 'PAID':
        logger.info("Order #%s is not PAID (status: %s) — skipping email.", order_id, order.payment_status)
        return

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'webmaster@localhost')
    subject = f'Order Confirmation — Order #{order.order_id}'
    message = (
        f"Hi {order.name},\n\n"
        f"Your payment of \u20b9{order.amount} has been received successfully.\n\n"
        f"Order ID: {order.order_id}\n"
        f"Status: {order.payment_status}\n\n"
        f"Thank you for shopping with MyAwesomeCart!\n\n"
        f"Best regards,\n"
        f"MyAwesomeCart Team"
    )

    try:
        send_mail(subject, message, from_email, [order.email], fail_silently=False)
        logger.info("Order confirmation email sent for Order #%s to %s", order_id, order.email)
    except Exception as exc:
        logger.error("Failed to send order confirmation email for Order #%s: %s", order_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_telegram_message(self, message):
    """Send a formatted message to the configured Telegram bot."""
    from telegram_bot import send_telegram_notification
    try:
        # Let send_telegram_notification handle requests/cooldowns
        # Use single attempt inside the function, raise on failure so Celery retries
        success = send_telegram_notification(message, max_retries=1)
        if not success:
            raise Exception("Telegram delivery failed in bot helper function.")
    except Exception as exc:
        logger.error("Telegram notification task failed, retrying: %s", exc)
        raise self.retry(exc=exc)


@shared_task
def send_restock_message(product_name, stock):
    """Format and dispatch a low-stock Telegram alert. (Legacy compatibility stub)"""
    msg = (
        f"⚠️ <b>RESTOCK ALERT (Legacy)</b> ⚠️\n\n"
        f"The product <b>{product_name}</b> is running low!\n"
        f"Remaining Stock: <b>{stock}</b>"
    )
    send_telegram_message.delay(msg)


@shared_task
def check_low_stock():
    """
    Periodic task: check all products whose stock is at or below
    their low_stock_threshold and send Telegram alerts for each (deduplicated).
    """
    from shop.models import Product
    from django.core.cache import cache

    low_stock_products = Product.objects.filter(
        stock__lte=F('low_stock_threshold'),
        is_active=True,
    )
    count = 0

    for product in low_stock_products:
        if product.stock == 0:
            cache_key = f"out_of_stock_alert_sent_{product.id}"
            if not cache.get(cache_key):
                alert_msg = (
                    f"🚨 <b>OUT OF STOCK ALERT</b> 🚨\n\n"
                    f"The product <b>{product.product_name}</b> is now out of stock!\n"
                    f"Please restock immediately."
                )
                send_telegram_message.delay(alert_msg)
                cache.set(cache_key, True, timeout=86400)
                count += 1
                logger.warning("LOW STOCK CHECK: '%s' is OUT OF STOCK. Alert queued.", product.product_name)
        else:
            cache_key = f"low_stock_alert_sent_{product.id}"
            if not cache.get(cache_key):
                recommended = max(0, max(10, product.low_stock_threshold * 5) - product.stock)
                alert_msg = (
                    f"⚠️ <b>LOW STOCK ALERT</b> ⚠️\n\n"
                    f"Product: <b>{product.product_name}</b>\n"
                    f"Current Stock: <b>{product.stock}</b>\n"
                    f"Minimum Threshold: <b>{product.low_stock_threshold}</b>\n"
                    f"Recommended Restock: <b>{recommended}</b>"
                )
                send_telegram_message.delay(alert_msg)
                cache.set(cache_key, True, timeout=86400)
                count += 1
                logger.warning("LOW STOCK CHECK: '%s' is LOW STOCK (%s/%s). Alert queued.",
                               product.product_name, product.stock, product.low_stock_threshold)

    logger.info("Low-stock check complete. %d alert(s) dispatched.", count)
    return f"{count} alert(s) dispatched."


@shared_task
def send_daily_inventory_summary():
    """
    Generate the daily inventory summary report and send it via Telegram.
    """
    from telegram_bot import generate_daily_summary_msg
    try:
        summary_msg = generate_daily_summary_msg()
        send_telegram_message.delay(summary_msg)
        logger.info("Daily inventory summary report dispatched to Celery task queue.")
        return "Daily summary sent successfully."
    except Exception as exc:
        logger.error("Failed to generate daily inventory summary: %s", exc)
        return f"Error: {exc}"

