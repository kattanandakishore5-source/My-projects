import os
import django
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myawesomecart.settings')
django.setup()

from shop.models import Product

TOKEN = "8630074417:AAGV8Kqgfn2HgheRgG5Yq0uW9RyEa9JI4fw"


async def check_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /check_stock command"""
    products = Product.objects.all()
    if not products:
        await update.message.reply_text("No products found in the database.")
        return

    message = "📊 <b>Current Inventory Status:</b>\n\n"
    for p in products:
        status = "✅" if p.stock > p.low_stock_threshold else "⚠️"
        message += f"{status} {p.product_name}: <b>{p.stock}</b> in stock\n"

    await update.message.reply_text(message, parse_mode="HTML")


def main():
    print("Starting Telegram Bot...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("check_stock", check_stock))
    print("Bot is polling... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()