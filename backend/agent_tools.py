"""
C3MR Agent Tools — Database query functions exposed as Claude tools.
Each function takes a DB session and returns structured data for the agent.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from .database import SessionLocal
from .models import (
    DbTarget, DbUser, DbReport, DbComment, DbAuditLog,
    TargetStatus, PaymentStatus, UserRole,
)
from .notifications import send_telegram_notification
from contextlib import contextmanager


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_dashboard_stats() -> dict:
    """Get current dashboard statistics."""
    with get_db() as db:
        total = db.query(func.count(DbTarget.id)).scalar() or 0
        pending = db.query(func.count(DbTarget.id)).filter(
            DbTarget.status == TargetStatus.pending
        ).scalar() or 0
        in_progress = db.query(func.count(DbTarget.id)).filter(
            DbTarget.status == TargetStatus.in_progress
        ).scalar() or 0
        completed = db.query(func.count(DbTarget.id)).filter(
            DbTarget.status == TargetStatus.completed
        ).scalar() or 0
        total_due = db.query(func.sum(DbTarget.amount_due)).scalar() or 0
        collected = db.query(func.sum(DbTarget.amount_due)).filter(
            DbTarget.status == TargetStatus.completed
        ).scalar() or 0
        officers = db.query(func.count(DbUser.id)).filter(
            DbUser.role == UserRole.officer
        ).scalar() or 0

    return {
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
    """List all officers with their workload stats."""
    with get_db() as db:
        officers = db.query(DbUser).filter(DbUser.role == UserRole.officer).all()
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
    limit: int = 20,
) -> list[dict]:
    """Query targets with flexible filters."""
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

        rows = q.order_by(DbTarget.created_at.desc()).limit(limit).all()
        return [
            {
                "id": t.id,
                "customer_name": t.customer_name,
                "address": t.address,
                "phone": t.phone,
                "amount_due": t.amount_due,
                "status": t.status.value if hasattr(t.status, "value") else t.status,
                "officer": u.name if u else "Unassigned",
            }
            for t, u in rows
        ]


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
        db.commit()

        # Notify officer via Telegram
        if officer.telegram_id and updated > 0:
            send_telegram_notification(
                officer.telegram_id,
                f"Anda mendapat {updated} target baru. Buka Aplikasi Lapangan untuk melihat.",
                include_field_app=True,
            )

        return {
            "success": True,
            "officer_name": officer.name,
            "targets_assigned": updated,
        }


def auto_assign_pending_targets(address_filter: str | None = None) -> dict:
    """Evenly distribute unassigned (pending) targets among all officers."""
    with get_db() as db:
        officers = db.query(DbUser).filter(DbUser.role == UserRole.officer).all()
        if not officers:
            return {"success": False, "error": "No officers available"}

        q = db.query(DbTarget).filter(
            DbTarget.status == TargetStatus.pending,
            DbTarget.assigned_officer.is_(None),
        )
        if address_filter:
            q = q.filter(DbTarget.address.ilike(f"%{address_filter}%"))

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

        db.commit()

        # Notify each officer
        summary = []
        for o in officers:
            count = len(assignments[o.id])
            if count > 0 and o.telegram_id:
                send_telegram_notification(
                    o.telegram_id,
                    f"Anda mendapat {count} target baru. Buka Aplikasi Lapangan untuk melihat.",
                    include_field_app=True,
                )
            summary.append({"officer": o.name, "new_assignments": count})

        return {
            "success": True,
            "total_assigned": len(pending),
            "distribution": summary,
        }


def assign_all_pending_to_officer(officer: str, address_filter: str | None = None) -> dict:
    """Assign ALL unassigned pending targets to a SINGLE officer (bulk).

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

        count = 0
        for target in q.all():
            target.assigned_officer = person.id
            target.status = TargetStatus.in_progress
            count += 1
        db.commit()

        if count > 0 and person.telegram_id:
            send_telegram_notification(
                person.telegram_id,
                f"Anda mendapat {count} target baru. Buka Aplikasi Lapangan untuk melihat.",
                include_field_app=True,
            )

        return {
            "success": True,
            "officer_name": person.name,
            "targets_assigned": count,
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


# Tool definitions for Claude API
TOOL_DEFINITIONS = [
    {
        "name": "get_dashboard_stats",
        "description": "Get current C3MR dashboard statistics including target counts, revenue, collection rate, and active officers.",
        "input_schema": {
            "type": "object",
            "properties": {},
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
        "description": "Search and filter collection targets. Can filter by customer name, status (pending/in_progress/completed), officer name, address, and minimum amount. Use customer_name to look up a specific target before assigning it.",
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
        "description": "Automatically distribute all unassigned pending targets evenly among officers based on current workload. Optionally filter by address area.",
        "input_schema": {
            "type": "object",
            "properties": {
                "address_filter": {
                    "type": "string",
                    "description": "Only assign targets whose address contains this text (e.g. 'Jakarta', 'Bekasi')",
                },
            },
            "required": [],
        },
    },
    {
        "name": "assign_all_pending_to_officer",
        "description": "Assign ALL unassigned pending targets to ONE specific officer (bulk). Use this when the user wants every remaining/pending target given to a single officer (e.g. 'assign all remaining tasks to Budi'). The officer is given by name or id. Optionally filter by address area. Returns only a count — prefer this over fetching every target id yourself.",
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
            },
            "required": ["officer"],
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
]

# Map tool names to functions
TOOL_FUNCTIONS = {
    "get_dashboard_stats": lambda **kw: get_dashboard_stats(),
    "list_officers": lambda **kw: list_officers(),
    "query_targets": lambda **kw: query_targets(**kw),
    "get_overdue_targets": lambda **kw: get_overdue_targets(**kw),
    "get_flagged_targets": lambda **kw: get_flagged_targets(**kw),
    "assign_targets_to_officer": lambda **kw: assign_targets_to_officer(**kw),
    "auto_assign_pending_targets": lambda **kw: auto_assign_pending_targets(**kw),
    "assign_all_pending_to_officer": lambda **kw: assign_all_pending_to_officer(**kw),
    "get_officer_performance": lambda **kw: get_officer_performance(**kw),
    "generate_daily_report": lambda **kw: generate_daily_report(),
}
