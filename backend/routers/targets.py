import csv
import io
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import DbTarget, DbComment, DbReport, DbUser, DbAuditLog, DbNotificationLog, Target, TargetCreate, TargetStatus, utc_iso
from ..security import require_manager

router = APIRouter()
logger = logging.getLogger(__name__)

def current_period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")

@router.get("/", response_model=List[Target])
async def get_targets(
    status: Optional[str] = None,
    period: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_manager),
):
    query = db.query(DbTarget)
    if status:
        query = query.filter(DbTarget.status == status)
    if period and period != "all":
        query = query.filter(DbTarget.period == period)
    return query.order_by(DbTarget.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/periods")
async def list_periods(db: Session = Depends(get_db), _auth: dict = Depends(require_manager)):
    """Distinct upload periods (newest first) with target counts, for the period selector."""
    rows = (
        db.query(DbTarget.period, func.count(DbTarget.id))
        .group_by(DbTarget.period)
        .all()
    )
    periods = sorted(
        [{"period": p or "lainnya", "total": c} for p, c in rows],
        key=lambda r: r["period"],
        reverse=True,
    )
    return {"periods": periods, "active": periods[0]["period"] if periods else None}

@router.post("/upload")
async def upload_targets(
    targets: List[TargetCreate],
    background_tasks: BackgroundTasks,
    period: Optional[str] = None,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_manager),
):
    batch_period = period or current_period()
    try:
        # Lewati baris yang sudah ada di periode ini. Tanpa ini, mengunggah berkas
        # yang sama dua kali — hal yang sangat mudah terjadi saat unggahan pertama
        # tampak gagal padahal berhasil — menggandakan seluruh batch, dan target
        # ganda berarti nasabah didatangi dua petugas.
        existing = {
            (c, a) for c, a in db.query(DbTarget.customer_name, DbTarget.address)
            .filter(DbTarget.period == batch_period).all()
        }
        fresh, skipped = [], 0
        for t in targets:
            key = (t.customerName, t.address)
            if key in existing:
                skipped += 1
                continue
            existing.add(key)
            fresh.append(t)
        targets = fresh

        db_targets = [
            DbTarget(
                customer_name=t.customerName,
                address=t.address,
                phone=t.phone,
                amount_due=t.amountDue,
                period=batch_period,
            )
            for t in targets
        ]
        db.add_all(db_targets)
        db.add(DbAuditLog(
            user_id=_auth["sub"], action="upload",
            detail=f"Mengunggah {len(targets)} target (periode {batch_period})"
                   + (f", {skipped} duplikat dilewati" if skipped else ""),
        ))
        db.commit()
        # Geocode alamat di background (Nominatim dibatasi 1 request/detik,
        # jadi tidak boleh menahan respons unggah).
        from ..external import geocode_targets
        background_tasks.add_task(geocode_targets, [t.id for t in db_targets])
        msg = f"Berhasil mengunggah {len(targets)} target ke periode {batch_period}"
        if skipped:
            msg += f" · {skipped} duplikat dilewati"
        return {"message": msg, "period": batch_period, "skipped": skipped}
    except Exception:
        db.rollback()
        # Detailnya ke log, bukan ke klien: str(e) dari psycopg2 memuat nama tabel,
        # nama kolom, dan nama constraint — peta skema gratis buat penyerang.
        logger.exception("Gagal mengunggah target")
        raise HTTPException(status_code=500, detail="Gagal mengunggah target.")

from ..notifications import send_telegram_notification
from ..lib.format import format_currency_python # We'll create this helper

def _resolve_officer(db, officer_id):
    """Ambil calon penerima tugas, dan pastikan ia memang petugas lapangan aktif.

    Sebelumnya kedua endpoint penugasan hanya mencari berdasarkan id. Target yang
    jatuh ke akun manajer/admin tidak pernah muncul di Mini App mana pun — dan
    karena statusnya berubah jadi 'sedang dikerjakan', ia juga hilang dari daftar
    yang menunggu ditugaskan. Nasabahnya tidak pernah didatangi tanpa satu pun
    tanda di dashboard.
    """
    officer = db.query(DbUser).filter(DbUser.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Petugas tidak ditemukan")
    role = officer.role.value if hasattr(officer.role, "value") else officer.role
    if role != "officer":
        raise HTTPException(status_code=400, detail="Target hanya bisa ditugaskan ke petugas lapangan")
    if not officer.active:
        raise HTTPException(status_code=400, detail="Petugas ini sudah nonaktif")
    return officer


def _assign_one(db_target, db_officer, db, auth_sub):
    """Assign a single target and send notification. Returns success bool."""
    db_target.assigned_officer = db_officer.id
    db_target.status = TargetStatus.in_progress
    db.add(DbAuditLog(user_id=auth_sub, action="assign", detail=f"Menugaskan '{db_target.customer_name}' ke {db_officer.name}"))

    if db_officer.telegram_id:
        formatted_amount = format_currency_python(db_target.amount_due)
        msg = (
            f"*Penugasan Baru*\n\n"
            f"Target: *{db_target.customer_name}*\n"
            f"Jumlah: *{formatted_amount}*\n"
            f"Lokasi: {db_target.address}\n\n"
            f"Silakan buka Aplikasi Lapangan C3MR untuk memulai proses penagihan."
        )
        success = send_telegram_notification(db_officer.telegram_id, msg, include_field_app=True)
        db.add(DbNotificationLog(recipient_id=db_officer.id, message=msg, success="true" if success else "false"))

@router.patch("/{target_id}/assign")
async def assign_target(target_id: str, officer_id: str, db: Session = Depends(get_db), _auth: dict = Depends(require_manager)):
    db_target = db.query(DbTarget).filter(DbTarget.id == target_id).first()
    if not db_target:
        raise HTTPException(status_code=404, detail="Target tidak ditemukan")
    db_officer = _resolve_officer(db, officer_id)

    _assign_one(db_target, db_officer, db, _auth["sub"])
    db.commit()
    return {"message": f"Target berhasil ditugaskan ke {db_officer.name}"}

from pydantic import BaseModel as _BaseModel

class BulkAssignPayload(_BaseModel):
    target_ids: List[str]
    officer_id: str

@router.post("/bulk-assign")
async def bulk_assign(payload: BulkAssignPayload, db: Session = Depends(get_db), _auth: dict = Depends(require_manager)):
    db_officer = _resolve_officer(db, payload.officer_id)

    targets = db.query(DbTarget).filter(DbTarget.id.in_(payload.target_ids)).all()
    if not targets:
        raise HTTPException(status_code=404, detail="Tidak ada target yang ditemukan")

    for t in targets:
        _assign_one(t, db_officer, db, _auth["sub"])
    db.commit()
    return {"message": f"{len(targets)} target berhasil ditugaskan ke {db_officer.name}"}

@router.get("/export/csv")
async def export_targets_csv(period: Optional[str] = None, db: Session = Depends(get_db), _auth: dict = Depends(require_manager)):
    query = db.query(DbTarget)
    if period and period != "all":
        query = query.filter(DbTarget.period == period)
    targets = query.order_by(DbTarget.created_at.desc()).all()
    users = {u.id: u.name for u in db.query(DbUser).all()}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Nama Nasabah", "Alamat", "Telepon", "Jumlah Tagihan", "Petugas", "Status", "Periode", "Dibuat Pada"])
    for t in targets:
        writer.writerow([
            t.id[:8],
            t.customer_name,
            t.address,
            t.phone,
            t.amount_due,
            users.get(t.assigned_officer, "-"),
            t.status.value if hasattr(t.status, "value") else t.status,
            t.period or "-",
            t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "",
        ])
    output.seek(0)
    db.add(DbAuditLog(
        user_id=_auth["sub"], action="export",
        detail=f"Mengekspor {len(targets)} target ke CSV (periode {period or 'semua'})",
    ))
    db.commit()

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=c3mr_targets_export.csv"},
    )

@router.get("/{target_id}/reports")
async def get_target_reports(target_id: str, db: Session = Depends(get_db), _auth: dict = Depends(require_manager)):
    reports = (
        db.query(DbReport, DbUser)
        .join(DbUser, DbReport.officer_id == DbUser.id)
        .filter(DbReport.target_id == target_id)
        .order_by(DbReport.submitted_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "payment_status": r.payment_status,
            "notes": r.notes,
            "photo_url": r.photo_url,
            "officerName": u.name,
            "distance_m": r.distance_m,
            "has_location": r.officer_lat is not None,
            "submitted_at": utc_iso(r.submitted_at),
        }
        for r, u in reports
    ]

@router.get("/{target_id}/comments")
async def get_target_comments(target_id: str, db: Session = Depends(get_db), _auth: dict = Depends(require_manager)):
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
            "created_at": utc_iso(c.created_at)
        }
        for c, u in comments
    ]
