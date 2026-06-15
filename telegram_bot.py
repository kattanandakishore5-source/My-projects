import os
import sys
import logging
import hashlib
import time
import requests
from decouple import config

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("telegram_bot")

# Fetch credentials from environment
TOKEN = config("TELEGRAM_BOT_TOKEN", default="YOUR_FALLBACK_TOKEN_HERE")
CHAT_ID = config("TELEGRAM_CHAT_ID", default="")


def owner_only(func):
    """
    Decorator to restrict access to bot commands to the owner (TELEGRAM_CHAT_ID).
    """
    async def wrapper(update, context):
        if not CHAT_ID:
            logger.error("TELEGRAM_CHAT_ID not configured in environment.")
            await update.message.reply_text("Error: TELEGRAM_CHAT_ID environment variable is missing.")
            return

        user_chat_id = str(update.effective_chat.id)
        if user_chat_id != str(CHAT_ID):
            logger.warning("Unauthorized access attempt from Chat ID: %s", user_chat_id)
            await update.message.reply_text("🚫 Unauthorized: You do not have permission to access this bot.")
            return
        return await func(update, context)
    return wrapper


# ─── Command Handlers ──────────────────────────────────────────────────

@owner_only
async def start_cmd(update, context):
    """Handler for the /start or /help command"""
    help_text = (
        "🤖 <b>Inventory Management Bot</b> 🤖\n\n"
        "Here are the available commands:\n"
        "• /check_stock - Show current stock levels of all active products.\n"
        "• /low_stock - Show list of products running below their minimum threshold.\n"
        "• /out_of_stock - Show list of products that are currently out of stock.\n"
        "• /daily_summary - Generate and send the daily inventory summary report.\n"
        "• /help - Display this help message."
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


@owner_only
async def check_stock(update, context):
    """Handler for the /check_stock command"""
    from shop.models import Product
    products = Product.objects.filter(is_active=True).order_by('product_name')
    if not products.exists():
        await update.message.reply_text("No active products found in the database.")
        return

    message = "📊 <b>Current Inventory Status:</b>\n\n"
    for p in products:
        if p.stock == 0:
            status = "🚨 (Out of Stock)"
        elif p.stock <= p.low_stock_threshold:
            status = "⚠️ (Low Stock)"
        else:
            status = "✅"
        message += f"{status} <b>{p.product_name}</b>: {p.stock} units (Threshold: {p.low_stock_threshold})\n"

    await update.message.reply_text(message, parse_mode="HTML")


@owner_only
async def low_stock(update, context):
    """Handler for the /low_stock command"""
    from shop.models import Product
    from django.db.models import F

    products = Product.objects.filter(is_active=True, stock__lte=F('low_stock_threshold'), stock__gt=0).order_by('product_name')
    if not products.exists():
        await update.message.reply_text("✅ All active products are sufficiently stocked.")
        return

    message = "⚠️ <b>Low Stock Products:</b>\n\n"
    for p in products:
        # Calculate dynamic recommended restock quantity (target of 5 * threshold)
        recommended = max(0, max(10, p.low_stock_threshold * 5) - p.stock)
        message += f"• <b>{p.product_name}</b>\n  Current Stock: <b>{p.stock}</b>\n  Threshold: <b>{p.low_stock_threshold}</b>\n  Rec. Restock: <b>{recommended}</b>\n\n"

    await update.message.reply_text(message, parse_mode="HTML")


@owner_only
async def out_of_stock(update, context):
    """Handler for the /out_of_stock command"""
    from shop.models import Product
    products = Product.objects.filter(is_active=True, stock=0).order_by('product_name')
    if not products.exists():
        await update.message.reply_text("✅ No products are out of stock.")
        return

    message = "🚨 <b>Out of Stock Products:</b>\n\n"
    for p in products:
        message += f"• <b>{p.product_name}</b>\n"

    await update.message.reply_text(message, parse_mode="HTML")


@owner_only
async def daily_summary(update, context):
    """Handler for the /daily_summary command"""
    await update.message.reply_chat_action(action="typing")
    try:
        summary_msg = generate_daily_summary_msg()
        await update.message.reply_text(summary_msg, parse_mode="HTML")
    except Exception as e:
        logger.exception("Error generating daily summary via bot command: %s", e)
        await update.message.reply_text("❌ Failed to generate daily summary due to an error.")


# ─── Integration Helpers ─────────────────────────────────────────────

def send_telegram_notification(message: str, max_retries: int = 3, retry_delay: int = 5) -> bool:
    """
    Sends a message to the configured Telegram Chat.
    Includes duplicate check, error handling, logging, and retry logic.
    """
    # Bypass sending actual HTTP requests when running unit tests
    try:
        from django.conf import settings
        if getattr(settings, 'TESTING', False) or getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            logger.info("[TEST MODE] Skipping actual Telegram API request: %s", message)
            return True
    except Exception:
        pass

    token = config('TELEGRAM_BOT_TOKEN', default='')
    chat_id = config('TELEGRAM_CHAT_ID', default='')

    if not token or not chat_id:
        logger.warning("Telegram Bot Token or Chat ID not configured. Skipping message.")
        return False

    # Prevent duplicate notifications within 30 seconds using django cache
    msg_hash = hashlib.md5(message.encode('utf-8')).hexdigest()
    cache_key = f"tg_msg_sent_{msg_hash}"
    try:
        from django.core.cache import cache
        if cache.get(cache_key):
            logger.info("Duplicate Telegram message detected (via hash) — skipping.")
            return True
    except Exception as cache_err:
        logger.warning("Failed to access cache for deduplication: %s", cache_err)
        cache_key = None

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    attempt = 0
    while attempt < max_retries:
        try:
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
            logger.info("Telegram notification successfully sent (Attempt %d/%d).", attempt + 1, max_retries)

            # Cache the message key on success to prevent immediate duplicate deliveries
            if cache_key:
                try:
                    cache.set(cache_key, True, timeout=30)
                except Exception:
                    pass
            return True
        except requests.exceptions.RequestException as err:
            attempt += 1
            logger.warning("Failed to send Telegram message (Attempt %d/%d): %s", attempt, max_retries, err)
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                logger.error("Failed to send Telegram message after %d attempts.", max_retries)

    return False


def generate_daily_summary_msg() -> str:
    """
    Generates a daily inventory summary report message.
    """
    from shop.models import Product, Orders, OrderUpdate
    from django.db.models import F
    from datetime import date

    # Total Active Products
    total_products = Product.objects.filter(is_active=True).count()

    # Low stock
    low_stock_products = Product.objects.filter(
        is_active=True,
        stock__lte=F('low_stock_threshold'),
        stock__gt=0
    ).order_by('product_name')
    low_stock_count = low_stock_products.count()

    # Out of stock
    out_of_stock_products = Product.objects.filter(is_active=True, stock=0).order_by('product_name')
    out_of_stock_count = out_of_stock_products.count()

    # Products sold today
    today = date.today()
    today_updates = OrderUpdate.objects.filter(timestamp=today, update_desc="The order has been placed")
    order_ids = [u.order_id for u in today_updates]
    orders = Orders.objects.filter(order_id__in=order_ids)

    sold_today = {}
    for order in orders:
        items = order.items_json or {}
        for prod_id, details in items.items():
            qty = details.get('qty', 0)
            name = details.get('name', 'Unknown Product')
            sold_today[name] = sold_today.get(name, 0) + qty

    # Format message
    msg = "📋 <b>DAILY INVENTORY SUMMARY</b> 📋\n\n"
    msg += f"• Total Active Products: <b>{total_products}</b>\n"
    msg += f"• Low-stock Products: <b>{low_stock_count}</b>\n"
    msg += f"• Out-of-stock Products: <b>{out_of_stock_count}</b>\n\n"

    if low_stock_count > 0:
        msg += "⚠️ <b>Low Stock Products:</b>\n"
        for p in low_stock_products:
            recommended = max(0, max(10, p.low_stock_threshold * 5) - p.stock)
            msg += f"  - {p.product_name} (Stock: {p.stock}, Threshold: {p.low_stock_threshold}, Rec. Restock: {recommended})\n"
        msg += "\n"

    if out_of_stock_count > 0:
        msg += "🚨 <b>Out of Stock Products:</b>\n"
        for p in out_of_stock_products:
            msg += f"  - {p.product_name}\n"
        msg += "\n"

    msg += "🛍️ <b>Products Sold Today:</b>\n"
    if sold_today:
        for name, qty in sold_today.items():
            msg += f"  - {name}: <b>{qty}</b> units\n"
    else:
        msg += "  - No sales recorded today.\n"

    return msg


def main():
    """Starts the Telegram bot polling mode."""
    # We initialize Django only if running as a standalone script
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myawesomecart.settings')
    import django
    django.setup()

    from telegram.ext import Application, CommandHandler

    print("Starting Telegram Bot...")
    if TOKEN == "YOUR_FALLBACK_TOKEN_HERE" or not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not configured in environment variables.")
        sys.exit(1)

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", start_cmd))
    app.add_handler(CommandHandler("check_stock", check_stock))
    app.add_handler(CommandHandler("low_stock", low_stock))
    app.add_handler(CommandHandler("out_of_stock", out_of_stock))
    app.add_handler(CommandHandler("daily_summary", daily_summary))

    print("Bot is polling... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
