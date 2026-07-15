from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import DbTarget, DbComment, DbUser, DashboardStats, TargetStatus, Target, utc_iso
from ..security import require_auth
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class DashboardSnapshot(BaseModel):
    stats: DashboardStats
    targets: List[Target]

@router.get("/", response_model=DashboardSnapshot)
async def get_dashboard_snapshot(period: Optional[str] = None, db: Session = Depends(get_db), _auth: dict = Depends(require_auth)):
    def base_query():
        q = db.query(DbTarget)
        if period and period != "all":
            q = q.filter(DbTarget.period == period)
        return q

    # 1. Fetch Stats (scoped to the selected period, if any)
    total_targets = base_query().count()
    completed = base_query().filter(DbTarget.status == TargetStatus.completed).count()
    in_progress = base_query().filter(DbTarget.status == TargetStatus.in_progress).count()
    pending = base_query().filter(DbTarget.status == TargetStatus.pending).count()

    stats = {
        "totalTargets": total_targets,
        "completed": completed,
        "inProgress": in_progress,
        "pending": pending
    }

    # 2. Fetch Targets for the dashboard table
    # Using the Pydantic Target model which handles the snake_case mapping
    targets = base_query().order_by(DbTarget.created_at.desc()).limit(50).all()

    return {
        "stats": stats,
        "targets": targets
    }

@router.get("/recent-comments")
async def get_recent_comments(limit: int = 5, db: Session = Depends(get_db), _auth: dict = Depends(require_auth)):
    comments = (
        db.query(DbComment, DbUser.name.label("officer_name"), DbTarget.customer_name)
        .join(DbUser, DbComment.officer_id == DbUser.id)
        .join(DbTarget, DbComment.target_id == DbTarget.id)
        .order_by(DbComment.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": c.id,
            "message": c.message,
            "tag": c.tag,
            "officerName": officer_name,
            "customerName": customer_name,
            "created_at": utc_iso(c.created_at),
        }
        for c, officer_name, customer_name in comments
    ]
