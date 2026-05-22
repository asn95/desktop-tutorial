from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import DbTarget, DbComment, DbUser, Target, TargetCreate, TargetStatus
from ..security import require_auth

router = APIRouter()

@router.get("/", response_model=List[Target])
async def get_targets(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
):
    query = db.query(DbTarget)
    if status:
        query = query.filter(DbTarget.status == status)
    return query.order_by(DbTarget.created_at.desc()).offset(skip).limit(limit).all()

@router.post("/upload")
async def upload_targets(targets: List[TargetCreate], db: Session = Depends(get_db), _auth: dict = Depends(require_auth)):
    try:
        db_targets = [
            DbTarget(
                customer_name=t.customerName,
                address=t.address,
                phone=t.phone,
                amount_due=t.amountDue,
            )
            for t in targets
        ]
        db.add_all(db_targets)
        db.commit()
        return {"message": f"Successfully uploaded {len(targets)} targets"}
    except Exception as e:
        db.rollback()
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to upload targets: {str(e)}")

from ..notifications import send_telegram_notification
from ..lib.format import format_currency_python # We'll create this helper

@router.patch("/{target_id}/assign")
async def assign_target(target_id: str, officer_id: str, db: Session = Depends(get_db), _auth: dict = Depends(require_auth)):
    db_target = db.query(DbTarget).filter(DbTarget.id == target_id).first()
    if not db_target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    # Verify officer exists
    db_officer = db.query(DbUser).filter(DbUser.id == officer_id).first()
    if not db_officer:
        raise HTTPException(status_code=404, detail="Officer not found")

    db_target.assigned_officer = officer_id
    db_target.status = TargetStatus.in_progress
    db.commit()

    # Send Notification if Telegram ID is available
    if db_officer.telegram_id:
        formatted_amount = format_currency_python(db_target.amount_due)
        msg = (
            f"🚨 *NEW ASSIGNMENT*\n\n"
            f"Target: *{db_target.customer_name}*\n"
            f"Amount: *{formatted_amount}*\n"
            f"Location: {db_target.address}\n\n"
            f"Open your C3MR Field App to begin collection."
        )
        send_telegram_notification(db_officer.telegram_id, msg, include_field_app=True)
    
    return {"message": f"Target assigned to {db_officer.name}"}

@router.get("/{target_id}/comments")
async def get_target_comments(target_id: str, db: Session = Depends(get_db), _auth: dict = Depends(require_auth)):
    comments = (
        db.query(DbComment, DbUser)
        .join(DbUser, DbComment.officer_id == DbUser.id)
        .filter(DbComment.target_id == target_id)
        .order_by(DbComment.created_at.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "message": c.message,
            "tag": c.tag,
            "officerName": u.name,
            "created_at": c.created_at.isoformat()
        }
        for c, u in comments
    ]
