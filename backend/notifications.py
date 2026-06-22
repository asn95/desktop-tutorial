import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

def send_telegram_notification(telegram_id: str, message: str, include_field_app: bool = False) -> bool:
    if not TOKEN:
        print("Telegram Bot Token not configured. Notification skipped.")
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": telegram_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    if include_field_app:
        mini_app_url = os.environ.get(
            "MINI_APP_URL",
            "https://c3mr-app-production-b353.up.railway.app/officer-app/"
        )
        payload["reply_markup"] = json.dumps({
            "inline_keyboard": [[
                {"text": "📋 Buka Aplikasi Lapangan", "web_app": {"url": mini_app_url}}
            ]]
        })

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")
        return False
