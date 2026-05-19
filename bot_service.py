import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# Replace with your actual Bot Token from @BotFather
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")

# This must be a publicly accessible URL for it to work in real Telegram
# For local testing, you usually need a tool like ngrok
MINI_APP_URL = "https://your-ngrok-url.ngrok-free.app/officer" 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [
            InlineKeyboardButton(
                "Open C3MR Field App", 
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Welcome {user.first_name} to C3MR System.\n\n"
        f"Your Telegram ID: `{user.id}`\n\n"
        "Click the button below to access your assigned collection tasks.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

if __name__ == "__main__":
    if TOKEN == "YOUR_BOT_TOKEN":
        print("Error: Please set your TELEGRAM_BOT_TOKEN in .env or bot_service.py")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        print("Bot is running... Press Ctrl+C to stop.")
        app.run_polling()
