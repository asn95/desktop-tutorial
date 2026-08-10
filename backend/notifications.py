import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

def send_telegram_notification(telegram_id: str, message: str, include_field_app: bool = False, parse_mode: str | None = "Markdown") -> bool:
    if not TOKEN:
        print("Telegram Bot Token not configured. Notification skipped.")
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": telegram_id,
        "text": message,
    }
    # AI-generated text may contain stray * or _ that break Telegram's Markdown
    # parser (message rejected) — callers pass parse_mode=None to send plain text.
    if parse_mode:
        payload["parse_mode"] = parse_mode

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

    # Dua percobaan dengan jeda pendek. Kegagalan Telegram yang paling sering
    # ditemui bersifat sesaat (jaringan, 429), dan sebelumnya kegagalan itu hanya
    # dicatat ke notification_logs lalu tidak pernah disentuh lagi — petugas
    # kehilangan penugasannya tanpa ada yang tahu.
    for attempt in (1, 2):
        try:
            # timeout wajib: ini panggilan sinkron yang dipakai di dalam request
            # handler (_assign_one, agent_tools._notify) — tanpa batas waktu,
            # Telegram yang menggantung menahan worker-nya selamanya.
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Telegram notification attempt {attempt} failed: {e}")
            if attempt == 1:
                time.sleep(2)
    return False
