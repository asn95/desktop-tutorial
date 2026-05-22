from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from ..database import get_db
from ..models import DbTarget, DbReport, DbUser, DbComment, TargetStatus, UserRole
from ..security import require_auth
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class StatusDistribution(BaseModel):
    name: str
    value: int

class OfficerPerformance(BaseModel):
    name: str
    assigned: int
    completed: int
    reports: int

class RevenueBreakdown(BaseModel):
    total_due: float
    collected: float
    outstanding: float
    collection_rate: float

class CommentTagCount(BaseModel):
    tag: str
    count: int

class AnalyticsSummary(BaseModel):
    distribution: List[StatusDistribution]
    total_revenue: float
    revenue: RevenueBreakdown
    officer_performance: List[OfficerPerformance]
    total_targets: int
    total_reports: int
    total_comments: int
    top_issues: List[CommentTagCount]

@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
):
    # Build base query with optional date filter
    base_q = db.query(DbTarget)
    if date_from:
        base_q = base_q.filter(DbTarget.created_at >= datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc))
    if date_to:
        base_q = base_q.filter(DbTarget.created_at < datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc).replace(hour=23, minute=59, second=59))

    # Status Distribution
    pending = base_q.filter(DbTarget.status == TargetStatus.pending).count()
    in_progress = base_q.filter(DbTarget.status == TargetStatus.in_progress).count()
    completed = base_q.filter(DbTarget.status == TargetStatus.completed).count()

    distribution = [
        {"name": "Pending", "value": pending},
        {"name": "In Progress", "value": in_progress},
        {"name": "Completed", "value": completed},
    ]

    # Revenue Breakdown (respects date filter)
    total_due = base_q.with_entities(func.coalesce(func.sum(DbTarget.amount_due), 0)).scalar()
    collected = base_q.filter(DbTarget.status == TargetStatus.completed).with_entities(func.coalesce(func.sum(DbTarget.amount_due), 0)).scalar()
    outstanding = total_due - collected
    collection_rate = (collected / total_due * 100) if total_due > 0 else 0

    # Officer Performance (optimized with joins instead of N+1 queries)
    from sqlalchemy.sql import func as fn

    officer_query = (
        db.query(
            DbUser.id,
            DbUser.name,
            fn.count(DbTarget.id).label("assigned"),
            fn.coalesce(fn.sum(case(
                (DbTarget.status == TargetStatus.completed, 1),
                else_=0
            )), 0).label("completed"),
        )
        .outerjoin(DbTarget, DbTarget.assigned_officer == DbUser.id)
        .filter(DbUser.role == UserRole.officer)
        .group_by(DbUser.id, DbUser.name)
        .all()
    )

    # Get report counts in one query
    report_map = dict(
        db.query(DbReport.officer_id, fn.count(DbReport.id))
        .group_by(DbReport.officer_id)
        .all()
    )

    officer_perf = []
    for oid, oname, assigned, comp in officer_query:
        reports = report_map.get(oid, 0)
        if assigned > 0 or reports > 0:
            officer_perf.append({
                "name": oname,
                "assigned": assigned,
                "completed": int(comp),
                "reports": reports,
            })

    # Totals
    total_targets = pending + in_progress + completed
    total_reports = db.query(DbReport).count()
    total_comments = db.query(DbComment).count()

    # Top Issues (comment tags)
    tag_counts = (
        db.query(DbComment.tag, func.count(DbComment.id).label("cnt"))
        .filter(DbComment.tag.isnot(None))
        .group_by(DbComment.tag)
        .order_by(func.count(DbComment.id).desc())
        .limit(5)
        .all()
    )
    tag_labels = {
        "wrong_address": "Alamat Salah",
        "wrong_phone": "Nomor Salah",
        "customer_moved": "Customer Pindah",
        "not_found": "Tidak Ditemukan",
        "other": "Lainnya",
    }
    top_issues = [{"tag": tag_labels.get(t, t), "count": c} for t, c in tag_counts]

    return {
        "distribution": distribution,
        "total_revenue": collected,
        "revenue": {
            "total_due": total_due,
            "collected": collected,
            "outstanding": outstanding,
            "collection_rate": round(collection_rate, 1),
        },
        "officer_performance": officer_perf,
        "total_targets": total_targets,
        "total_reports": total_reports,
        "total_comments": total_comments,
        "top_issues": top_issues,
    }
