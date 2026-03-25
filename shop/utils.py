import requests

def send_telegram_message(message):
    """Sends a formatted message to your Telegram bot."""
    token = "8630074417:AAGV8Kqgfn2HgheRgG5Yq0uW9RyEa9JI4fw"
    chat_id = "7250990789"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Telegram notification failed: {e}")

def send_restock_message(product_name, stock):
    """Specific formatter for low stock alerts."""
    msg = (
        f"⚠️ <b>RESTOCK ALERT</b> ⚠️\n\n"
        f"The product <b>{product_name}</b> is running low!\n"
        f"Remaining Stock: <b>{stock}</b>"
    )
    send_telegram_message(msg)