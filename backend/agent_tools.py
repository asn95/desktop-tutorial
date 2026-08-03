"""
C3MR Agent Tools — Database query functions exposed as Claude tools.
Each function takes a DB session and returns structured data for the agent.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from .database import SessionLocal
from .models import (
    DbTarget, DbUser, DbReport, DbComment, DbAuditLog, DbNotificationLog,
    TargetStatus, PaymentStatus, UserRole,
)
from .notifications import send_telegram_notification
from contextlib import contextmanager
import contextvars

# Siapa yang sedang menyuruh agen. Diisi run_agent() dari endpoint web maupun
# handler bot, dibaca oleh action tool agar aksinya tercatat di audit log atas
# nama manusia yang memerintahkannya — bukan atas nama "agen" tanpa pemilik.
CURRENT_ACTOR = contextvars.ContextVar("c3mr_agent_actor", default=None)


def _log_action(db, action: str, detail: str) -> None:
    """Catat aksi agen ke audit log, kalau pemanggilnya diketahui."""
    actor = CURRENT_ACTOR.get()
    if actor:
        db.add(DbAuditLog(user_id=actor, action=action, detail=detail))


def _notify(db, officer, message: str, include_field_app: bool = True) -> bool:
    """Kirim notifikasi DAN catat hasilnya, meniru jalur REST di routers/targets.py.

    Petugas tanpa telegram_id tetap dicatat sebagai gagal, supaya penugasan yang
    tidak sampai ke siapa pun tidak hilang diam-diam."""
    if not officer.telegram_id:
        db.add(DbNotificationLog(recipient_id=officer.id, message=message, success="false"))
        return False
    ok = send_telegram_notification(officer.telegram_id, message, include_field_app=include_field_app)
    db.add(DbNotificationLog(recipient_id=officer.id, message=message,
                             success="true" if ok else "false"))
    return ok


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def extract_area(address: str) -> str:
    """Best-effort city/area from 'Jl. X No. 12 Banda Aceh' or 'Jl. Y No. 5, Jakarta Selatan'."""
    if not address:
        return "Lainnya"
    if "," in address:
        tail = address.rsplit(",", 1)[1].strip()
        if tail:
            return tail
    tokens = address.replace(",", " ").split()
    last_numeric = -1
    for i, tok in enumerate(tokens):
        if any(ch.isdigit() for ch in tok):
            last_numeric = i
    if last_numeric != -1 and last_numeric < len(tokens) - 1:
        return " ".join(tokens[last_numeric + 1:])
    return tokens[-1] if tokens else "Lainnya"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Jarak lingkaran-besar antara dua koordinat, dalam kilometer."""
    import math
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    a = (math.sin((rlat2 - rlat1) / 2) ** 2
         + math.cos(rlat1) * math.cos(rlat2) * math.sin((rlon2 - rlon1) / 2) ** 2)
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def _days_since(dt) -> int:
    """Whole days since a stored datetime; tolerates naive (UTC) and aware values."""
    if not dt:
        return 0
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        now = now.replace(tzinfo=None)
    return max((now - dt).days, 0)


def _active_period(db) -> str | None:
    """Newest upload period in the DB ("YYYY-MM"), i.e. the batch currently being worked."""
    periods = [p for (p,) in db.query(DbTarget.period).distinct().all() if p]
    return max(periods) if periods else None


def get_dashboard_stats(period: str | None = None) -> dict:
    """Get current dashboard statistics, optionally scoped to one monthly period ("YYYY-MM")."""
    pf = [DbTarget.period == period] if period and period != "all" else []
    with get_db() as db:
        total = db.query(func.count(DbTarget.id)).filter(*pf).scalar() or 0
        pending = db.query(func.count(DbTarget.id)).filter(
            DbTarget.status == TargetStatus.pending, *pf
        ).scalar() or 0
        in_progress = db.query(func.count(DbTarget.id)).filter(
            DbTarget.status == TargetStatus.in_progress, *pf
        ).scalar() or 0
        completed = db.query(func.count(DbTarget.id)).filter(
            DbTarget.status == TargetStatus.completed, *pf
        ).scalar() or 0
        total_due = db.query(func.sum(DbTarget.amount_due)).filter(*pf).scalar() or 0
        collected = db.query(func.sum(DbTarget.amount_due)).filter(
            DbTarget.status == TargetStatus.completed, *pf
        ).scalar() or 0
        officers = db.query(func.count(DbUser.id)).filter(
            DbUser.role == UserRole.officer
        ).scalar() or 0
        available_periods = sorted(
            [p for (p,) in db.query(DbTarget.period).distinct().all() if p],
            reverse=True,
        )

    return {
        "period": period or "all",
        "available_periods": available_periods,
        "total_targets": total,
        "pending": pending,
        "in_progress": in_progress,
        "completed": completed,
        "total_due": total_due,
        "collected": collected,
        "outstanding": total_due - collected,
        "collection_rate": round(collected / total_due * 100, 1) if total_due else 0,
        "active_officers": officers,
    }


def list_officers() -> list[dict]:
    """List active officers with their workload stats."""
    with get_db() as db:
        officers = db.query(DbUser).filter(
            DbUser.role == UserRole.officer, DbUser.active == True
        ).all()
        result = []
        for o in officers:
            assigned = db.query(func.count(DbTarget.id)).filter(
                DbTarget.assigned_officer == o.id
            ).scalar() or 0
            completed = db.query(func.count(DbTarget.id)).filter(
                DbTarget.assigned_officer == o.id,
                DbTarget.status == TargetStatus.completed,
            ).scalar() or 0
            in_progress = db.query(func.count(DbTarget.id)).filter(
                DbTarget.assigned_officer == o.id,
                DbTarget.status == TargetStatus.in_progress,
            ).scalar() or 0
            result.append({
                "id": o.id,
                "name": o.name,
                "telegram_id": o.telegram_id,
                "assigned": assigned,
                "completed": completed,
                "in_progress": in_progress,
                "completion_rate": round(completed / assigned * 100, 1) if assigned else 0,
            })
    return result


def query_targets(
    status: str | None = None,
    customer_name: str | None = None,
    officer_name: str | None = None,
    address_contains: str | None = None,
    min_amount: float | None = None,
    period: str | None = None,
    limit: int = 20,
) -> dict:
    """Query targets with flexible filters.

    Mengembalikan objek, bukan list, supaya pemanggil tahu total sebenarnya dan
    tahu bila daftarnya terpotong oleh `limit`."""
    with get_db() as db:
        q = db.query(DbTarget, DbUser).outerjoin(
            DbUser, DbTarget.assigned_officer == DbUser.id
        )
        if status:
            q = q.filter(DbTarget.status == TargetStatus(status))
        if customer_name:
            q = q.filter(DbTarget.customer_name.ilike(f"%{customer_name}%"))
        if officer_name:
            q = q.filter(DbUser.name.ilike(f"%{officer_name}%"))
        if address_contains:
            q = q.filter(DbTarget.address.ilike(f"%{address_contains}%"))
        if min_amount:
            q = q.filter(DbTarget.amount_due >= min_amount)
        if period and period != "all":
            q = q.filter(DbTarget.period == period)

        # Hitung total SEBELUM limit. Tanpa ini pemanggil hanya melihat daftar
        # terpotong dan bisa menyimpulkan panjangnya sebagai jumlah seluruhnya.
        total = q.count()
        rows = q.order_by(DbTarget.created_at.desc()).limit(limit).all()
        items = [
            {
                "id": t.id,
                "customer_name": t.customer_name,
                "address": t.address,
                "phone": t.phone,
                "amount_due": t.amount_due,
                "status": t.status.value if hasattr(t.status, "value") else t.status,
                "officer": u.name if u else "Unassigned",
                "period": t.period,
            }
            for t, u in rows
        ]
        return {
            "total_matching": total,
            "showing": len(items),
            "truncated": total > len(items),
            "targets": items,
        }


def get_overdue_targets(days: int = 7) -> list[dict]:
    """Get targets that have been in_progress or pending for more than N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with get_db() as db:
        rows = (
            db.query(DbTarget, DbUser)
            .outerjoin(DbUser, DbTarget.assigned_officer == DbUser.id)
            .filter(
                DbTarget.status.in_([TargetStatus.pending, TargetStatus.in_progress]),
                DbTarget.created_at < cutoff,
            )
            .order_by(DbTarget.amount_due.desc())
            .all()
        )
        return [
            {
                "id": t.id,
                "customer_name": t.customer_name,
                "address": t.address,
                "amount_due": t.amount_due,
                "status": t.status.value if hasattr(t.status, "value") else t.status,
                "officer": u.name if u else "Unassigned",
                "days_old": (datetime.now(timezone.utc) - t.created_at).days,
            }
            for t, u in rows
        ]


def get_flagged_targets(min_comments: int = 3) -> list[dict]:
    """Get targets with many comments (potential issues needing attention)."""
    with get_db() as db:
        subq = (
            db.query(DbComment.target_id, func.count(DbComment.id).label("cnt"))
            .group_by(DbComment.target_id)
            .having(func.count(DbComment.id) >= min_comments)
            .subquery()
        )
        rows = (
            db.query(DbTarget, DbUser, subq.c.cnt)
            .join(subq, DbTarget.id == subq.c.target_id)
            .outerjoin(DbUser, DbTarget.assigned_officer == DbUser.id)
            .filter(DbTarget.status != TargetStatus.completed)
            .order_by(subq.c.cnt.desc())
            .all()
        )
        return [
            {
                "id": t.id,
                "customer_name": t.customer_name,
                "address": t.address,
                "amount_due": t.amount_due,
                "officer": u.name if u else "Unassigned",
                "comment_count": cnt,
                "status": t.status.value if hasattr(t.status, "value") else t.status,
            }
            for t, u, cnt in rows
        ]


def assign_targets_to_officer(target_ids: list[str], officer_id: str) -> dict:
    """Assign a list of targets to an officer. Returns success count."""
    with get_db() as db:
        officer = db.query(DbUser).filter(DbUser.id == officer_id).first()
        if not officer:
            return {"success": False, "error": "Officer not found"}

        updated = 0
        for tid in target_ids:
            target = db.query(DbTarget).filter(DbTarget.id == tid).first()
            if target:
                target.assigned_officer = officer_id
                if target.status == TargetStatus.pending:
                    target.status = TargetStatus.in_progress
                updated += 1
        if updated > 0:
            _log_action(db, "assign",
                        f"Agen menugaskan {updated} target ke {officer.name}")
            _notify(db, officer,
                    f"Anda mendapat {updated} target baru. Buka Aplikasi Lapangan untuk melihat.")
        db.commit()

        return {
            "success": True,
            "officer_name": officer.name,
            "targets_assigned": updated,
        }


def auto_assign_pending_targets(address_filter: str | None = None, period: str | None = None) -> dict:
    """Evenly distribute unassigned (pending) targets among all officers."""
    with get_db() as db:
        officers = db.query(DbUser).filter(
            DbUser.role == UserRole.officer, DbUser.active == True
        ).all()
        if not officers:
            return {"success": False, "error": "No officers available"}

        q = db.query(DbTarget).filter(
            DbTarget.status == TargetStatus.pending,
            DbTarget.assigned_officer.is_(None),
        )
        if address_filter:
            q = q.filter(DbTarget.address.ilike(f"%{address_filter}%"))
        if period and period != "all":
            q = q.filter(DbTarget.period == period)

        pending = q.all()
        if not pending:
            return {"success": True, "message": "No unassigned pending targets found"}

        # Get current workload per officer
        workloads = {}
        for o in officers:
            active = db.query(func.count(DbTarget.id)).filter(
                DbTarget.assigned_officer == o.id,
                DbTarget.status.in_([TargetStatus.pending, TargetStatus.in_progress]),
            ).scalar() or 0
            workloads[o.id] = active

        # Assign to officer with least workload (round-robin with balancing)
        assignments = {o.id: [] for o in officers}
        for target in pending:
            least_busy = min(workloads, key=workloads.get)
            target.assigned_officer = least_busy
            target.status = TargetStatus.in_progress
            assignments[least_busy].append(target.id)
            workloads[least_busy] += 1

        summary = []
        for o in officers:
            count = len(assignments[o.id])
            if count > 0:
                _notify(db, o,
                        f"Anda mendapat {count} target baru. Buka Aplikasi Lapangan untuk melihat.")
            summary.append({"officer": o.name, "new_assignments": count})
        _log_action(db, "assign",
                    f"Agen membagikan {len(pending)} target pending ke "
                    f"{sum(1 for o in officers if assignments[o.id])} petugas")
        db.commit()

        return {
            "success": True,
            "total_assigned": len(pending),
            "distribution": summary,
        }


def assign_all_pending_to_officer(officer: str, address_filter: str | None = None,
                                  period: str | None = None, limit: int | None = None) -> dict:
    """Assign unassigned pending targets to a SINGLE officer.

    `limit` menugaskan HANYA sebanyak itu (yang paling prioritas lebih dulu). Tanpa
    `limit` seluruh target pending yang cocok ikut tertugaskan — jadi ketika pengguna
    menyebut angka, angka itu WAJIB diteruskan ke sini.

    `officer` may be the officer's id or name (case-insensitive partial match).
    Returns only a summary count — never the full target list — so the result
    stays small and the agent request never exceeds provider payload limits.
    """
    with get_db() as db:
        person = db.query(DbUser).filter(
            DbUser.role == UserRole.officer, DbUser.id == officer
        ).first()
        if not person:
            person = db.query(DbUser).filter(
                DbUser.role == UserRole.officer, DbUser.name.ilike(f"%{officer}%")
            ).first()
        if not person:
            return {"success": False, "error": f"Officer '{officer}' not found"}

        q = db.query(DbTarget).filter(
            DbTarget.status == TargetStatus.pending,
            DbTarget.assigned_officer.is_(None),
        )
        if address_filter:
            q = q.filter(DbTarget.address.ilike(f"%{address_filter}%"))
        if period and period != "all":
            q = q.filter(DbTarget.period == period)

        # Yang tunggakannya terbesar didahulukan, supaya "tugaskan 5" memberi
        # lima yang paling berarti, bukan lima yang kebetulan paling awal.
        q = q.order_by(DbTarget.amount_due.desc())
        matching = q.count()
        rows = q.limit(limit).all() if limit and limit > 0 else q.all()

        count = 0
        for target in rows:
            target.assigned_officer = person.id
            target.status = TargetStatus.in_progress
            count += 1

        if count > 0:
            _log_action(db, "assign",
                        f"Agen menugaskan semua {count} target pending ke {person.name}")
            _notify(db, person,
                    f"Anda mendapat {count} target baru. Buka Aplikasi Lapangan untuk melihat.")
        db.commit()

        return {
            "success": True,
            "officer_name": person.name,
            "targets_assigned": count,
            "still_unassigned": max(matching - count, 0),
        }


def get_officer_performance(days: int = 30) -> list[dict]:
    """Get officer performance stats for the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with get_db() as db:
        officers = db.query(DbUser).filter(DbUser.role == UserRole.officer).all()
        result = []
        for o in officers:
            total_assigned = db.query(func.count(DbTarget.id)).filter(
                DbTarget.assigned_officer == o.id,
            ).scalar() or 0
            completed = db.query(func.count(DbTarget.id)).filter(
                DbTarget.assigned_officer == o.id,
                DbTarget.status == TargetStatus.completed,
            ).scalar() or 0
            reports = db.query(func.count(DbReport.id)).filter(
                DbReport.officer_id == o.id,
                DbReport.submitted_at >= cutoff,
            ).scalar() or 0
            comments = db.query(func.count(DbComment.id)).filter(
                DbComment.officer_id == o.id,
                DbComment.created_at >= cutoff,
            ).scalar() or 0
            collected = db.query(func.sum(DbTarget.amount_due)).filter(
                DbTarget.assigned_officer == o.id,
                DbTarget.status == TargetStatus.completed,
            ).scalar() or 0

            result.append({
                "name": o.name,
                "total_assigned": total_assigned,
                "completed": completed,
                "completion_rate": round(completed / total_assigned * 100, 1) if total_assigned else 0,
                "reports_submitted": reports,
                "comments": comments,
                "revenue_collected": collected,
            })

        result.sort(key=lambda x: x["completion_rate"], reverse=True)
    return result


def generate_daily_report() -> str:
    """Generate a formatted daily report text."""
    stats = get_dashboard_stats()
    perf = get_officer_performance(days=1)
    overdue = get_overdue_targets(days=7)

    lines = [
        "C3MR DAILY REPORT",
        f"Date: {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "OVERVIEW",
        f"  Total Targets: {stats['total_targets']}",
        f"  Completed: {stats['completed']}",
        f"  In Progress: {stats['in_progress']}",
        f"  Pending: {stats['pending']}",
        f"  Collection Rate: {stats['collection_rate']}%",
        f"  Revenue Collected: Rp {stats['collected']:,.0f}",
        f"  Outstanding: Rp {stats['outstanding']:,.0f}",
        "",
        f"OVERDUE TARGETS (>{7} days): {len(overdue)}",
    ]
    for t in overdue[:5]:
        lines.append(f"  - {t['customer_name']} (Rp {t['amount_due']:,.0f}) — {t['days_old']}d — {t['officer']}")

    lines.append("")
    lines.append("OFFICER PERFORMANCE (today)")
    for o in perf:
        lines.append(f"  - {o['name']}: {o['completed']}/{o['total_assigned']} ({o['completion_rate']}%)")

    return "\n".join(lines)


def get_priority_targets(officer: str | None = None, period: str | None = None, limit: int = 10) -> dict:
    """Rank targets by visit priority: amount due, days outstanding, broken
    promise-to-pay, repeat not-home, and area clustering (route efficiency).
    Defaults to the newest (active) upload period."""
    limit = min(max(int(limit or 10), 1), 20)
    with get_db() as db:
        if not period:
            period = _active_period(db)

        q = db.query(DbTarget, DbUser).outerjoin(
            DbUser, DbTarget.assigned_officer == DbUser.id
        ).filter(DbTarget.status != TargetStatus.completed)
        if period and period != "all":
            q = q.filter(DbTarget.period == period)
        if officer:
            q = q.filter(
                (DbUser.name.ilike(f"%{officer}%")) | (DbTarget.assigned_officer == officer)
            )
        rows = q.all()
        if not rows:
            return {"period": period or "all", "targets": [], "message": "Tidak ada target aktif yang cocok"}

        # One pass over recent reports for promise-to-pay / not-home history
        target_ids = [t.id for t, _ in rows]
        reports = db.query(DbReport).filter(DbReport.target_id.in_(target_ids)).all()
        promises: dict[str, int] = {}   # target_id -> days since oldest unfulfilled promise
        not_home: dict[str, int] = {}
        for r in reports:
            status = r.payment_status.value if hasattr(r.payment_status, "value") else r.payment_status
            if status == PaymentStatus.promise_to_pay.value:
                age = _days_since(r.submitted_at)
                promises[r.target_id] = max(promises.get(r.target_id, 0), age)
            elif status == PaymentStatus.not_home.value:
                not_home[r.target_id] = not_home.get(r.target_id, 0) + 1

        area_counts: dict[str, int] = {}
        for t, _ in rows:
            area = extract_area(t.address)
            area_counts[area] = area_counts.get(area, 0) + 1

        # Tetangga dalam radius 3 km (koordinat hasil geocoding Nominatim);
        # target tanpa koordinat memakai fallback nama area.
        CLUSTER_KM = 3.0
        located = [(t.id, t.latitude, t.longitude) for t, _ in rows
                   if t.latitude is not None and t.longitude is not None]
        neighbors: dict[str, int] = {}
        for tid, lat, lon in located:
            neighbors[tid] = sum(
                1 for oid, olat, olon in located
                if oid != tid and _haversine_km(lat, lon, olat, olon) <= CLUSTER_KM
            )

        max_amount = max(t.amount_due or 0 for t, _ in rows) or 1
        scored = []
        for t, u in rows:
            area = extract_area(t.address)
            age_days = _days_since(t.created_at)
            reasons = []

            amount_pts = (t.amount_due or 0) / max_amount * 40
            if amount_pts >= 20:
                reasons.append(f"Tunggakan besar (Rp {int(t.amount_due):,})".replace(",", "."))

            age_pts = min(age_days, 30) / 30 * 20
            if age_days >= 7:
                reasons.append(f"Sudah {age_days} hari belum tertagih")

            promise_pts = 0
            promise_age = promises.get(t.id)
            if promise_age is not None and promise_age >= 3:
                promise_pts = 30
                reasons.append(f"Janji bayar sudah lewat ({promise_age} hari lalu)")

            not_home_pts = 5 if not_home.get(t.id) else 0
            if not_home.get(t.id):
                reasons.append(f"{not_home[t.id]}x tidak di rumah, perlu waktu kunjungan berbeda")

            cluster_pts = 0
            if t.id in neighbors:  # punya koordinat → pakai jarak nyata
                if neighbors[t.id] >= 2:
                    cluster_pts = 5
                    reasons.append(f"{neighbors[t.id]} target lain dalam radius {CLUSTER_KM:g} km (sekali jalan)")
            elif area_counts.get(area, 0) >= 3:
                cluster_pts = 5
                reasons.append(f"{area_counts[area]} target di area {area} (sekali jalan)")

            scored.append({
                "id": t.id[:8],
                "target_id": t.id,
                "customer_name": t.customer_name,
                "area": area,
                "address": t.address,
                "phone": t.phone,
                "amount_due": t.amount_due,
                "status": t.status.value if hasattr(t.status, "value") else t.status,
                "officer": u.name if u else "Belum ditugaskan",
                "days_outstanding": age_days,
                "latitude": t.latitude,
                "longitude": t.longitude,
                "score": round(amount_pts + age_pts + promise_pts + not_home_pts + cluster_pts, 1),
                "reasons": reasons,
            })

        scored.sort(key=lambda r: (-r["score"], r["area"]))
        return {"period": period or "all", "scoring": "tunggakan 40% + umur 20% + janji-bayar-lewat 30 poin + tidak-di-rumah 5 + klaster lokasi 5 (radius 3 km via koordinat GPS, fallback nama area)", "targets": scored[:limit]}


def summarize_field_feedback(days: int = 30, limit: int = 50) -> dict:
    """Recent officer field comments with tags/areas plus aggregate counts, so the
    agent can summarize field issues (wrong address, customer moved, etc)."""
    days = min(max(int(days or 30), 1), 180)
    limit = min(max(int(limit or 50), 1), 100)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with get_db() as db:
        rows = (
            db.query(DbComment, DbTarget, DbUser)
            .join(DbTarget, DbComment.target_id == DbTarget.id)
            .join(DbUser, DbComment.officer_id == DbUser.id)
            .filter(DbComment.created_at >= cutoff)
            .order_by(DbComment.created_at.desc())
            .limit(limit)
            .all()
        )

        tag_counts: dict[str, int] = {}
        by_area: dict[str, dict[str, int]] = {}
        comments = []
        for c, t, u in rows:
            tag = c.tag or "tanpa_tag"
            area = extract_area(t.address)
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            by_area.setdefault(area, {})[tag] = by_area.get(area, {}).get(tag, 0) + 1
            comments.append({
                "date": c.created_at.strftime("%Y-%m-%d") if c.created_at else "-",
                "officer": u.name,
                "customer": t.customer_name,
                "area": area,
                "tag": tag,
                "message": (c.message or "")[:160],
            })

        return {
            "window_days": days,
            "total_comments": len(comments),
            "tag_counts": tag_counts,
            "issues_by_area": by_area,
            "comments": comments,
        }


def _nearest_neighbor_route(coords: list[tuple[float, float]]) -> tuple[list[int], list[dict]]:
    """Fallback urutan kunjungan bila OSRM tidak tersedia: tetangga terdekat
    (haversine), estimasi waktu dengan asumsi 40 km/jam jalan lapangan."""
    order = [0]
    remaining = set(range(1, len(coords)))
    while remaining:
        last = order[-1]
        nxt = min(remaining, key=lambda j: _haversine_km(*coords[last], *coords[j]))
        order.append(nxt)
        remaining.remove(nxt)
    legs = []
    for a, b in zip(order, order[1:]):
        km = _haversine_km(*coords[a], *coords[b])
        legs.append({"km": round(km, 1), "minutes": round(km / 40 * 60)})
    return order, legs


def plan_visit_route(
    officer: str,
    period: str | None = None,
    limit: int = 10,
    send_to_officer: bool = False,
) -> dict:
    """Susun urutan kunjungan optimal untuk satu petugas: mulai dari target
    prioritas tertinggi, sisanya diurutkan agar total perjalanan lewat jalan
    nyata (OSRM) sependek mungkin. Opsional: kirim rutenya ke Telegram petugas."""
    limit = min(max(int(limit or 10), 2), 12)
    pri = get_priority_targets(officer=officer, period=period, limit=20)
    targets = pri.get("targets", [])
    if not targets:
        return {"period": pri.get("period"), "stops": [],
                "message": f"Tidak ada target aktif untuk petugas '{officer}'."}

    routable = [t for t in targets if t.get("latitude") is not None and t.get("longitude") is not None][:limit]
    skipped = [t["customer_name"] for t in targets[:limit] if t.get("latitude") is None]

    if len(routable) < 2:
        return {
            "period": pri.get("period"),
            "stops": [],
            "message": "Kurang dari 2 target yang punya koordinat — belum bisa disusun rutenya. "
                       "Koordinat terisi otomatis setelah unggah CSV.",
            "targets_without_coordinates": skipped,
        }

    # Urutan input = urutan prioritas; titik pertama (prioritas tertinggi) jadi start tetap.
    coords = [(t["latitude"], t["longitude"]) for t in routable]
    from .external import plan_trip
    trip = plan_trip(coords)
    if trip:
        order, legs = trip["order"], trip["legs"]
        method = "OSRM (jarak & waktu tempuh jalan nyata)"
        total_km, total_minutes = trip["total_km"], trip["total_minutes"]
    else:
        order, legs = _nearest_neighbor_route(coords)
        method = "estimasi garis lurus/tetangga terdekat (OSRM sedang tidak tersedia)"
        total_km = round(sum(l["km"] for l in legs), 1)
        total_minutes = sum(l["minutes"] for l in legs)

    stops = []
    for seq, input_idx in enumerate(order):
        t = routable[input_idx]
        stops.append({
            "order": seq + 1,
            "customer_name": t["customer_name"],
            "area": t["area"],
            "address": t["address"],
            "phone": t["phone"],
            "amount_due": t["amount_due"],
            "priority_score": t["score"],
            "priority_reasons": t["reasons"],
            "travel_from_previous": legs[seq - 1] if seq > 0 else None,
        })

    result = {
        "officer": routable[0]["officer"],
        "period": pri.get("period"),
        "method": method,
        "start_rule": "Perhentian pertama = target dengan skor prioritas tertinggi.",
        "total_km": total_km,
        "total_minutes": total_minutes,
        "stops": stops,
        "targets_without_coordinates": skipped,
    }

    if send_to_officer:
        with get_db() as db:
            db_officer = (
                db.query(DbUser)
                .filter(DbUser.role == UserRole.officer, DbUser.name.ilike(f"%{officer}%"))
                .first()
            )
        if not db_officer or not db_officer.telegram_id:
            result["sent_to_officer"] = False
            result["send_note"] = "Petugas tidak ditemukan atau belum menautkan Telegram."
        else:
            lines = [f"🗺️ RUTE KUNJUNGAN — {db_officer.name}",
                     f"Periode {result['period']} · {len(stops)} lokasi · ±{total_km} km / {total_minutes} menit", ""]
            for s in stops:
                if s["travel_from_previous"]:
                    leg = s["travel_from_previous"]
                    lines.append(f"   ↓ {leg['km']} km · ±{leg['minutes']} mnt")
                amount = f"Rp {int(s['amount_due']):,}".replace(",", ".")
                lines.append(f"{s['order']}. {s['customer_name']} — {s['area']} ({amount})")
            lines += ["", "Urutan: prioritas tertinggi dulu, lalu rute jalan terpendek."]
            ok = send_telegram_notification(db_officer.telegram_id, "\n".join(lines), parse_mode=None)
            result["sent_to_officer"] = bool(ok)

    return result


def get_upcoming_holidays(days: int = 30) -> dict:
    """Indonesian national holidays in the next N days (Nager.Date, free API),
    so the agent can plan visit schedules around tanggal merah."""
    from .external import upcoming_holidays
    days = min(max(int(days or 30), 1), 366)
    holidays = upcoming_holidays(days)
    return {
        "window_days": days,
        "count": len(holidays),
        "holidays": holidays,
        "note": "Hanya libur nasional resmi; cuti bersama tidak termasuk."
        if holidays else f"Tidak ada libur nasional dalam {days} hari ke depan.",
    }


# Tool definitions for Claude API
TOOL_DEFINITIONS = [
    {
        "name": "get_dashboard_stats",
        "description": "Get current C3MR dashboard statistics including target counts, revenue, collection rate, and active officers. Targets are grouped into monthly upload periods; the result lists available_periods. Pass period to scope stats to one month, or omit for all-time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Monthly upload period in YYYY-MM format (e.g. '2026-07'). Omit or 'all' for every period.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "list_officers",
        "description": "List all field officers with their workload: assigned targets, completed, in-progress, and completion rate.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "query_targets",
        "description": "Search and filter collection targets. Returns an object: total_matching is the REAL number of targets matching the filters, targets is at most `limit` of them, and truncated says whether rows were left out. For counting questions always use total_matching, never the length of targets. To get counts by status for a period, get_dashboard_stats is cheaper and exact. Can filter by customer name, status (pending/in_progress/completed), officer name, address, and minimum amount. Use customer_name to look up a specific target before assigning it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed"],
                    "description": "Filter by target status",
                },
                "customer_name": {
                    "type": "string",
                    "description": "Filter by customer name (partial, case-insensitive match)",
                },
                "officer_name": {
                    "type": "string",
                    "description": "Filter by officer name (partial match)",
                },
                "address_contains": {
                    "type": "string",
                    "description": "Filter targets whose address contains this text",
                },
                "min_amount": {
                    "type": "number",
                    "description": "Minimum amount_due filter",
                },
                "period": {
                    "type": "string",
                    "description": "Filter by monthly upload period, YYYY-MM format (e.g. '2026-07'). Omit for all periods.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 20)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_overdue_targets",
        "description": "Get targets that have been pending or in-progress for more than N days. Useful for follow-up and escalation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to consider overdue (default 7)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_flagged_targets",
        "description": "Get targets with many officer comments, indicating potential issues (wrong address, customer complaints, etc).",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_comments": {
                    "type": "integer",
                    "description": "Minimum number of comments to flag (default 3)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "assign_targets_to_officer",
        "description": "Assign specific targets to an officer by their IDs. Notifies the officer via Telegram.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of target IDs to assign",
                },
                "officer_id": {
                    "type": "string",
                    "description": "The officer's user ID",
                },
            },
            "required": ["target_ids", "officer_id"],
        },
    },
    {
        "name": "auto_assign_pending_targets",
        "description": "Automatically distribute all unassigned pending targets evenly among officers based on current workload. Optionally filter by address area and/or monthly period.",
        "input_schema": {
            "type": "object",
            "properties": {
                "address_filter": {
                    "type": "string",
                    "description": "Only assign targets whose address contains this text (e.g. 'Jakarta', 'Bekasi')",
                },
                "period": {
                    "type": "string",
                    "description": "Only assign targets from this monthly upload period, YYYY-MM format (e.g. '2026-07'). Omit for all periods.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "assign_all_pending_to_officer",
        "description": "Assign unassigned pending targets to ONE specific officer. If the user names a number (\"assign 5 to Atta\"), pass it as `limit` — never assign more than the user asked for. Without `limit` this assigns EVERY remaining/pending target given to a single officer (e.g. 'assign all remaining tasks to Budi'). The officer is given by name or id. Optionally filter by address area. Returns only a count — prefer this over fetching every target id yourself.",
        "input_schema": {
            "type": "object",
            "properties": {
                "officer": {
                    "type": "string",
                    "description": "Officer name (partial match) or officer id to receive all pending targets",
                },
                "address_filter": {
                    "type": "string",
                    "description": "Only assign targets whose address contains this text (e.g. 'Jakarta')",
                },
                "period": {
                    "type": "string",
                    "description": "Only assign targets from this monthly upload period, YYYY-MM format (e.g. '2026-07'). Omit for all periods.",
                },
                    "limit": {
                        "type": "integer",
                        "description": "Assign at most this many targets, highest amount due first. Use it whenever the user names a quantity.",
                    },
            },
            "required": ["officer"],
        },
    },
    {
        "name": "get_priority_targets",
        "description": "Rank the highest-priority targets to visit today. Scores each active (non-completed) target by amount due, days outstanding, broken promise-to-pay, repeat not-home visits, and same-area clustering for route efficiency. Use when the manager asks which targets to visit first / today's priorities. Defaults to the newest (active) upload period.",
        "input_schema": {
            "type": "object",
            "properties": {
                "officer": {
                    "type": "string",
                    "description": "Optional: limit to targets assigned to this officer (name partial match or id)",
                },
                "period": {
                    "type": "string",
                    "description": "Monthly period YYYY-MM. Omit for the active (newest) batch; 'all' for every period.",
                },
                "limit": {
                    "type": "integer",
                    "description": "How many top targets to return (default 10, max 20)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "summarize_field_feedback",
        "description": "Fetch recent officer field comments (wrong address, customer moved, wrong phone, etc) with per-tag and per-area counts. Use when the manager asks to summarize field feedback, complaints, or data-quality issues reported by officers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Look-back window in days (default 30, max 180)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max comments to fetch (default 50, max 100)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_officer_performance",
        "description": "Get detailed performance metrics for all officers: completion rate, reports submitted, revenue collected.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Look-back period in days (default 30)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "generate_daily_report",
        "description": "Generate a full daily operations report with overview stats, overdue targets, and officer performance.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "plan_visit_route",
        "description": "Plan the optimal visit route (urutan kunjungan) for ONE officer's active targets. Starts at the officer's highest-priority target, then orders remaining stops to minimize real road travel (OSRM road distances & drive times; falls back to straight-line estimates if OSRM is down). Use when the manager asks for a visit route/order ('rute kunjungan', 'urutan kunjungan') for an officer. Set send_to_officer=true ONLY when the manager explicitly asks to send/share the route to the officer's Telegram.",
        "input_schema": {
            "type": "object",
            "properties": {
                "officer": {
                    "type": "string",
                    "description": "Officer name (partial match) or id — required, route is per officer",
                },
                "period": {
                    "type": "string",
                    "description": "Monthly period YYYY-MM. Omit for the active (newest) batch.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max stops in the route (default 10, min 2, max 12)",
                },
                "send_to_officer": {
                    "type": "boolean",
                    "description": "If true, also push the route as a Telegram message to the officer (default false)",
                },
            },
            "required": ["officer"],
        },
    },
    {
        "name": "get_upcoming_holidays",
        "description": "List upcoming Indonesian national holidays (tanggal merah) within the next N days, with day names and how many days away. Use when planning visit schedules, answering 'kapan libur', or checking whether a planned visit day is a holiday. Official national holidays only (no cuti bersama).",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Look-ahead window in days (default 30, max 366)",
                },
            },
            "required": [],
        },
    },
]

# Map tool names to functions
TOOL_FUNCTIONS = {
    "get_dashboard_stats": lambda **kw: get_dashboard_stats(**kw),
    "list_officers": lambda **kw: list_officers(),
    "query_targets": lambda **kw: query_targets(**kw),
    "get_overdue_targets": lambda **kw: get_overdue_targets(**kw),
    "get_flagged_targets": lambda **kw: get_flagged_targets(**kw),
    "assign_targets_to_officer": lambda **kw: assign_targets_to_officer(**kw),
    "auto_assign_pending_targets": lambda **kw: auto_assign_pending_targets(**kw),
    "assign_all_pending_to_officer": lambda **kw: assign_all_pending_to_officer(**kw),
    "get_priority_targets": lambda **kw: get_priority_targets(**kw),
    "summarize_field_feedback": lambda **kw: summarize_field_feedback(**kw),
    "get_officer_performance": lambda **kw: get_officer_performance(**kw),
    "generate_daily_report": lambda **kw: generate_daily_report(),
    "get_upcoming_holidays": lambda **kw: get_upcoming_holidays(**kw),
    "plan_visit_route": lambda **kw: plan_visit_route(**kw),
}
