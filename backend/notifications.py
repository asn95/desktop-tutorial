import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

def send_telegram_notification(telegram_id: str, message: str):
    if not TOKEN:
        print("Telegram Bot Token not configured. Notification skipped.")
        return
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": telegram_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")
