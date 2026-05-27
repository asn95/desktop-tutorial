"""
C3MR Manager Bot - Telegram Bot for managers to receive notifications
and query collection statistics.

Commands:
  /start   - Welcome message
  /summary - Daily collection statistics
  /report  - Recent field reports
"""
import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from sqlalchemy import func, text
from .database import SessionLocal
from .models import DbTarget, DbReport, DbUser, TargetStatus, PaymentStatus

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

from contextlib import contextmanager

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_manager(telegram_id: str, db) -> bool:
    """Check if the Telegram user is a registered manager or officer with access."""
    user = db.query(DbUser).filter(
        DbUser.telegram_id == telegram_id
    ).first()
    if not user:
        return False
    # Managers always have access
    if user.role == "manager":
        return True
    # Also allow specific officer IDs set via env (comma-separated)
    allowed = os.environ.get("MANAGER_BOT_ALLOWED_IDS", "")
    if allowed and telegram_id in allowed.split(","):
        return True
    return False

async def require_manager(update: Update) -> bool:
    """Gate check — returns True if authorized, sends denial if not."""
    tid = str(update.effective_user.id)
    with get_db() as db:
        if is_manager(tid, db):
            return True
    await update.message.reply_text(
        "⛔ *Access Denied*\n\n"
        "This command is restricted to authorized managers only\\.\n"
        "Your Telegram ID is not registered as a manager in the C3MR system\\.",
        parse_mode="MarkdownV2"
    )
    return False

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tid = str(user.id)

    with get_db() as db:
        mgr = is_manager(tid, db)

    if mgr:
        web_url = os.environ.get("WEB_ADMIN_URL", "https://c3mr-app-production.up.railway.app")
        keyboard = [[
            InlineKeyboardButton("Open Web Dashboard", url=web_url)
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Welcome, *{user.first_name}*\\!\n\n"
            "🔐 *C3MR Manager Console*\n\n"
            "Available commands:\n"
            "  /summary \\- Collection statistics\n"
            "  /report  \\- Recent field reports\n\n"
            "Or open the full dashboard below\\.",
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            f"Hello, {user.first_name}\\.\n\n"
            "⛔ You are not registered as a manager\\.\n"
            f"Your Telegram ID: `{tid}`\n\n"
            "Please contact your administrator to get access\\.",
            parse_mode="MarkdownV2"
        )

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_manager(update):
        return
    try:
        with get_db() as db:
            total = db.query(func.count(DbTarget.id)).scalar() or 0
            pending = db.query(func.count(DbTarget.id)).filter(DbTarget.status == TargetStatus.pending).scalar() or 0
            in_progress = db.query(func.count(DbTarget.id)).filter(DbTarget.status == TargetStatus.in_progress).scalar() or 0
            completed = db.query(func.count(DbTarget.id)).filter(DbTarget.status == TargetStatus.completed).scalar() or 0

            total_due = db.query(func.sum(DbTarget.amount_due)).scalar() or 0
            collected = db.query(func.sum(DbTarget.amount_due)).filter(DbTarget.status == TargetStatus.completed).scalar() or 0

            officers = db.query(func.count(DbUser.id)).filter(DbUser.role == "officer").scalar() or 0

        msg = (
            f"📊 *C3MR Daily Summary*\n\n"
            f"*Targets*\n"
            f"  Total: {total}\n"
            f"  Pending: {pending}\n"
            f"  In Progress: {in_progress}\n"
            f"  Completed: {completed}\n\n"
            f"*Revenue*\n"
            f"  Total Due: Rp {total_due:,.0f}\n"
            f"  Collected: Rp {collected:,.0f}\n\n"
            f"*Officers Active*: {officers}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in summary_command: {e}")
        await update.message.reply_text("Failed to retrieve summary. Please try again later.")

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_manager(update):
        return
    try:
        with get_db() as db:
            recent = (
                db.query(DbReport, DbTarget, DbUser)
                .join(DbTarget, DbReport.target_id == DbTarget.id)
                .join(DbUser, DbReport.officer_id == DbUser.id)
                .order_by(DbReport.submitted_at.desc())
                .limit(5)
                .all()
            )

        if not recent:
            await update.message.reply_text("No reports submitted yet.")
            return

        lines = ["📋 *Recent Field Reports*\n"]
        for report, target, officer in recent:
            lines.append(
                f"• *{target.customer_name}*\n"
                f"  Officer: {officer.name}\n"
                f"  Status: {report.payment_status.value if hasattr(report.payment_status, 'value') else report.payment_status}\n"
                f"  Notes: {report.notes or '-'}\n"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        print(f"Error in report_command: {e}")
        await update.message.reply_text("Failed to retrieve reports. Please try again later.")

def run_bot():
    if not TOKEN:
        print("TELEGRAM_BOT_TOKEN not set. Bot not started.", flush=True)
        return

    import time as _time
    import requests as _req

    # Delete webhook and wait for previous deploy's polling to expire
    try:
        _req.post(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook",
                  json={"drop_pending_updates": True}, timeout=5)
    except Exception:
        pass

    # Wait long enough for the old container's long-poll to time out (default 30s)
    print("Waiting 35s for previous container to release polling lock...", flush=True)
    _time.sleep(35)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("report", report_command))

    print("C3MR Manager Bot is running...", flush=True)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    run_bot()
