from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import DbTarget, DbComment, DbUser, DashboardStats, TargetStatus, Target
from ..security import require_auth
from pydantic import BaseModel
from typing import List

router = APIRouter()

class DashboardSnapshot(BaseModel):
    stats: DashboardStats
    targets: List[Target]

@router.get("/", response_model=DashboardSnapshot)
async def get_dashboard_snapshot(db: Session = Depends(get_db), _auth: dict = Depends(require_auth)):
    # 1. Fetch Stats
    total_targets = db.query(DbTarget).count()
    completed = db.query(DbTarget).filter(DbTarget.status == TargetStatus.completed).count()
    in_progress = db.query(DbTarget).filter(DbTarget.status == TargetStatus.in_progress).count()
    pending = db.query(DbTarget).filter(DbTarget.status == TargetStatus.pending).count()
    
    stats = {
        "totalTargets": total_targets,
        "completed": completed,
        "inProgress": in_progress,
        "pending": pending
    }

    # 2. Fetch Targets for the dashboard table
    # Using the Pydantic Target model which handles the snake_case mapping
    targets = db.query(DbTarget).order_by(DbTarget.created_at.desc()).limit(50).all()
    
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
            "created_at": c.created_at.isoformat(),
        }
        for c, officer_name, customer_name in comments
    ]
