"""
C3MR Manager Bot - Bot Telegram untuk notifikasi dan statistik collection
bagi manajer.

Perintah:
  /start   - Pesan sambutan
  /summary - Statistik collection harian
  /report  - Laporan lapangan terbaru
  /ask     - Kueri bahasa alami & otomasi alur kerja bertenaga AI
"""
import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
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


def format_payment_status(status) -> str:
    value = status.value if hasattr(status, "value") else status
    return {
        "Promise to Pay": "Janji Bayar",
        "Paid": "Lunas",
        "Refused": "Menolak",
        "Not Home": "Tidak di Rumah",
        "Partial Payment": "Bayar Sebagian",
    }.get(value, value)

async def require_manager(update: Update) -> bool:
    """Gate check — returns True if authorized, sends denial if not."""
    tid = str(update.effective_user.id)
    with get_db() as db:
        if is_manager(tid, db):
            return True
    await update.message.reply_text(
        "⛔ *Akses Ditolak*\n\n"
        "Perintah ini hanya untuk manajer yang berwenang\\.\n"
        "Telegram ID Anda belum terdaftar sebagai manajer di sistem C3MR\\.",
        parse_mode="MarkdownV2"
    )
    return False

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tid = str(user.id)

    with get_db() as db:
        mgr = is_manager(tid, db)

    if mgr:
        web_url = os.environ.get("WEB_ADMIN_URL", "https://c3mr-app-production-b353.up.railway.app")
        keyboard = [[
            InlineKeyboardButton("Buka Dasbor Web", url=web_url)
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Selamat datang, *{user.first_name}*\\!\n\n"
            "🔐 *Konsol Manajer C3MR*\n\n"
            "Perintah yang tersedia:\n"
            "  /summary \\- Statistik collection\n"
            "  /report  \\- Laporan lapangan terbaru\n"
            "  /ask     \\- Asisten AI bahasa alami\n\n"
            "Atau langsung ketik pertanyaan\\!",
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            f"Halo, {user.first_name}\\.\n\n"
            "⛔ Anda belum terdaftar sebagai manajer\\.\n"
            f"Telegram ID Anda: `{tid}`\n\n"
            "Silakan hubungi administrator untuk mendapatkan akses\\.",
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
            f"📊 *Ringkasan Harian C3MR*\n\n"
            f"*Target*\n"
            f"  Total: {total}\n"
            f"  Menunggu: {pending}\n"
            f"  Sedang Berjalan: {in_progress}\n"
            f"  Selesai: {completed}\n\n"
            f"*Pendapatan*\n"
            f"  Total Tagihan: Rp {total_due:,.0f}\n"
            f"  Tertagih: Rp {collected:,.0f}\n\n"
            f"*Petugas Aktif*: {officers}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in summary_command: {e}")
        await update.message.reply_text("Gagal mengambil ringkasan. Silakan coba lagi nanti.")

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
            await update.message.reply_text("Belum ada laporan yang dikirim.")
            return

        lines = ["📋 *Laporan Lapangan Terbaru*\n"]
        for report, target, officer in recent:
            lines.append(
                f"• *{target.customer_name}*\n"
                f"  Petugas: {officer.name}\n"
                f"  Status: {format_payment_status(report.payment_status)}\n"
                f"  Catatan: {report.notes or '-'}\n"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        print(f"Error in report_command: {e}")
        await update.message.reply_text("Gagal mengambil laporan. Silakan coba lagi nanti.")

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ask <question> — AI-powered workflow agent."""
    if not await require_manager(update):
        return

    # Get the question text after /ask
    question = " ".join(context.args) if context.args else ""
    if not question:
        await update.message.reply_text(
            "Cara pakai: /ask <pertanyaan Anda>\n\n"
            "Contoh:\n"
            "  /ask Berapa collection rate kita?\n"
            "  /ask Target mana yang sudah jatuh tempo?\n"
            "  /ask Tugaskan otomatis target pending Jakarta\n"
            "  /ask Siapa petugas dengan kinerja terbaik?\n"
            "  /ask Buat laporan harian"
        )
        return

    # Show typing indicator
    await update.message.chat.send_action("typing")

    try:
        from .agent import run_agent
        response = await run_agent(question)

        # Telegram max message is 4096 chars
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await update.message.reply_text(response[i:i + 4000])
        else:
            await update.message.reply_text(response)
    except Exception as e:
        print(f"Agent error: {e}", flush=True)
        await update.message.reply_text(
            f"Kesalahan agen: {str(e)[:200]}\n\n"
            "Pastikan ANTHROPIC_API_KEY sudah diatur di environment."
        )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages as agent queries (if from a manager)."""
    tid = str(update.effective_user.id)
    with get_db() as db:
        if not is_manager(tid, db):
            return  # Silently ignore non-manager messages

    question = update.message.text.strip()
    if not question:
        return

    await update.message.chat.send_action("typing")

    try:
        from .agent import run_agent
        response = await run_agent(question)
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await update.message.reply_text(response[i:i + 4000])
        else:
            await update.message.reply_text(response)
    except Exception as e:
        print(f"Agent error: {e}", flush=True)
        await update.message.reply_text(f"Kesalahan agen: {str(e)[:200]}")


def run_bot():
    if not TOKEN:
        print("TELEGRAM_BOT_TOKEN belum diatur. Bot tidak dijalankan.", flush=True)
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
    print("Menunggu 35 detik agar container sebelumnya melepas polling lock...", flush=True)
    _time.sleep(35)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    print("Bot Manajer C3MR berjalan dengan Agen AI...", flush=True)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    run_bot()
