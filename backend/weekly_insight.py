"""
C3MR Weekly Insight — proactive Monday-morning AI report for managers.

Collects this-week vs last-week collection numbers, area and officer signals,
and field feedback, then has Claude write a short Indonesian narrative that is
sent to every manager on Telegram. Also exposed as the /mingguan bot command.
"""
from datetime import datetime, timedelta, timezone

import anthropic

from .agent import _get_client, MODEL, _clean
from .agent_tools import (
    get_db, extract_area, _active_period,
    get_priority_targets, summarize_field_feedback,
)
from .models import DbTarget, DbReport, DbUser, DbNotificationLog, TargetStatus, PaymentStatus, UserRole
from .notifications import send_telegram_notification
from .lib.format import format_currency_python

WIB = timezone(timedelta(hours=7))

NARRATIVE_SYSTEM_PROMPT = """You write the weekly operations briefing for C3MR, a debt-collection field operation (IndiHome by Telkomsel).

You receive raw JSON metrics. Write a short briefing for the manager.

RULES:
- Bahasa Indonesia only.
- PLAIN TEXT ONLY — no markdown symbols (*, _, #, `). Use the bullet character • and line breaks.
- Structure: 1) ringkasan performa minggu ini vs minggu lalu (sebutkan angka), 2) area terbaik & area yang tertinggal, 3) petugas yang perlu perhatian, 4) masalah lapangan (jika ada), 5) catatan cuaca di area fokus & hari libur nasional minggu ini (hanya jika datanya ada — kaitkan dengan jadwal kunjungan), 6) tiga rekomendasi aksi konkret.
- Ground every claim in the JSON numbers — never invent data. If a section has no data, say so briefly.
- Amounts in the JSON are plain Rupiah values. Convert units carefully: 36250000 = Rp 36,25 juta (NOT miliar); 1500000000 = Rp 1,5 miliar. Double-check every juta/miliar label.
- Max 3000 characters. Concise, direct, professional but warm.
"""


def _week_report_counts(db, start, end) -> dict:
    """Payment-status counts + paid amount for reports submitted in [start, end)."""
    rows = (
        db.query(DbReport, DbTarget)
        .join(DbTarget, DbReport.target_id == DbTarget.id)
        .filter(DbReport.submitted_at >= start, DbReport.submitted_at < end)
        .all()
    )
    counts: dict[str, int] = {}
    paid_amount = 0.0
    for r, t in rows:
        status = r.payment_status.value if hasattr(r.payment_status, "value") else r.payment_status
        counts[status] = counts.get(status, 0) + 1
        if status == PaymentStatus.paid.value:
            paid_amount += t.amount_due or 0
    return {"reports": len(rows), "by_status": counts, "paid_amount": paid_amount}


def collect_weekly_data() -> dict:
    """Gather all metrics the narrative is written from."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # DB stores naive UTC
    week_start = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)

    with get_db() as db:
        period = _active_period(db)

        this_week = _week_report_counts(db, week_start, now)
        last_week = _week_report_counts(db, prev_week_start, week_start)

        # Active-period target counts
        pf = [DbTarget.period == period] if period else []
        total = db.query(DbTarget).filter(*pf).count()
        completed = db.query(DbTarget).filter(DbTarget.status == TargetStatus.completed, *pf).count()
        pending = db.query(DbTarget).filter(DbTarget.status == TargetStatus.pending, *pf).count()
        in_progress = db.query(DbTarget).filter(DbTarget.status == TargetStatus.in_progress, *pf).count()

        # Outstanding value per area (active period, not completed)
        area_outstanding: dict[str, dict] = {}
        for t in db.query(DbTarget).filter(DbTarget.status != TargetStatus.completed, *pf).all():
            area = extract_area(t.address)
            slot = area_outstanding.setdefault(area, {"targets": 0, "amount": 0.0})
            slot["targets"] += 1
            slot["amount"] += t.amount_due or 0
        top_areas = sorted(area_outstanding.items(), key=lambda kv: -kv[1]["amount"])[:5]

        # Officer activity this week: reports submitted vs active workload
        officers = db.query(DbUser).filter(DbUser.role == UserRole.officer).all()
        officer_rows = []
        for o in officers:
            active = db.query(DbTarget).filter(
                DbTarget.assigned_officer == o.id,
                DbTarget.status.in_([TargetStatus.pending, TargetStatus.in_progress]),
            ).count()
            reports_this_week = db.query(DbReport).filter(
                DbReport.officer_id == o.id, DbReport.submitted_at >= week_start
            ).count()
            officer_rows.append({
                "name": o.name,
                "active_targets": active,
                "reports_this_week": reports_this_week,
            })

    # Target menua: belum selesai dan sudah lebih dari 14 hari sejak dibuat.
    # Dihitung di sini, bukan diserahkan ke narasi AI, supaya angkanya tetap terbit
    # apa adanya meskipun panggilan modelnya gagal.
    with get_db() as db:
        stale_cut = now - timedelta(days=14)
        stale_q = (
            db.query(DbTarget)
            .filter(DbTarget.status != TargetStatus.completed, DbTarget.created_at < stale_cut)
            .order_by(DbTarget.created_at.asc())
        )
        stale_all = stale_q.all()
        stale = {
            "count": len(stale_all),
            "amount": round(sum(t.amount_due or 0 for t in stale_all)),
            "oldest_days": (now - stale_all[0].created_at).days if stale_all else 0,
            "sample": [
                {"customer": t.customer_name, "days": (now - t.created_at).days,
                 "amount": t.amount_due, "area": extract_area(t.address)}
                for t in stale_all[:5]
            ],
        }

    feedback = summarize_field_feedback(days=7, limit=30)
    feedback.pop("comments", None)  # aggregates are enough for the narrative
    priorities = get_priority_targets(limit=5)

    # Cuaca 3 hari di area tunggakan teratas (Open-Meteo) + libur nasional 7 hari
    # ke depan (Nager.Date). Keduanya opsional: laporan tetap terbit tanpa mereka.
    from .external import geocode_address, get_weather, upcoming_holidays
    weather_rows = []
    for a, _v in top_areas[:3]:
        if a == "Lainnya":
            continue
        coords = geocode_address(a)
        w = get_weather(*coords, days=3) if coords else None
        if w:
            weather_rows.append({"area": a, **w})
    holidays = upcoming_holidays(7)

    return {
        "generated_at_wib": datetime.now(WIB).strftime("%A %d %B %Y %H:%M"),
        "active_period": period,
        "active_period_targets": {
            "total": total, "completed": completed,
            "in_progress": in_progress, "pending": pending,
        },
        "this_week": this_week,
        "last_week": last_week,
        "top_outstanding_areas": [
            {"area": a, "targets": v["targets"], "outstanding_amount": v["amount"]}
            for a, v in top_areas
        ],
        "officers": officer_rows,
        "field_feedback_7d": feedback,
        "stale_targets_over_14d": stale,
        "weather_3d_top_areas": weather_rows,
        "national_holidays_next_7d": holidays,
        "top_priority_targets": [
            {"customer": t["customer_name"], "area": t["area"], "amount_due": t["amount_due"], "reasons": t["reasons"]}
            for t in priorities.get("targets", [])
        ],
    }


async def build_weekly_report_text() -> str:
    """Collect data and have Claude write the Indonesian narrative."""
    import json
    data = collect_weekly_data()
    try:
        response = await _get_client().messages.create(
            model=MODEL,
            max_tokens=1500,
            system=NARRATIVE_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": "Tulis briefing mingguan dari data berikut:\n" + json.dumps(data, default=str, ensure_ascii=False),
            }],
        )
        narrative = _clean("".join(b.text for b in response.content if b.type == "text"))
    except Exception as e:
        # Report must still reach managers even when the AI call fails
        narrative = (
            f"(Narasi AI tidak tersedia: {type(e).__name__}.)\n\n"
            f"Angka utama periode {data.get('active_period') or '-'}:\n"
            f"• Target: {data['active_period_targets']}\n"
            f"• Laporan minggu ini: {data['this_week']}\n"
            f"• Laporan minggu lalu: {data['last_week']}"
        )

    range_end = datetime.now(WIB)
    range_start = range_end - timedelta(days=7)
    header = (
        "📊 LAPORAN MINGGUAN C3MR\n"
        f"{range_start.strftime('%d %b')} – {range_end.strftime('%d %b %Y')}"
        + (f" · Periode aktif {data['active_period']}" if data.get("active_period") else "")
        + "\n\n"
    )
    stale = data.get("stale_targets_over_14d") or {}
    aging = ""
    if stale.get("count"):
        lines = "\n".join(
            f"  • {r['customer']} — {r['days']} hari · {format_currency_python(r['amount'])} · {r['area']}"
            for r in stale.get("sample", [])
        )
        aging = (
            f"\n\n⏳ TARGET MENUA (>14 hari, belum selesai)\n"
            f"{stale['count']} target · {format_currency_python(stale['amount'])} tertahan · "
            f"tertua {stale['oldest_days']} hari\n{lines}"
        )
    return header + narrative + aging


async def send_weekly_report() -> dict:
    """Build the report and push it to every manager who has a Telegram ID."""
    text = await build_weekly_report_text()

    with get_db() as db:
        managers = (
            db.query(DbUser)
            .filter(DbUser.role == UserRole.manager, DbUser.telegram_id.isnot(None))
            .all()
        )

    sent, failed = [], []
    with get_db() as db:
        for m in managers:
            ok = send_telegram_notification(m.telegram_id, text, parse_mode=None)
            (sent if ok else failed).append(m.name)
            # Laporan mingguan juga notifikasi: tanpa baris ini pengirimannya
            # tidak meninggalkan jejak sama sekali.
            db.add(DbNotificationLog(recipient_id=m.id, message=text,
                                     success="true" if ok else "false"))
        db.commit()

    return {"sent_to": sent, "failed": failed, "chars": len(text)}
