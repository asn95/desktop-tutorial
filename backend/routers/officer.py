from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form, Header
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import shutil
import os
import uuid
import json
from urllib.parse import parse_qsl
from ..database import get_db
from ..models import DbTarget, DbUser, DbReport, DbComment, DbNotificationLog, Target, TargetStatus, PaymentStatus, UserRole, utc_iso
from ..security import validate_telegram_data

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = "backend/uploads"

# Disalin dari bot_service.format_payment_status alih-alih diimpor: bot_service
# mengimpor paket `telegram` di tingkat modul, dan menariknya ke jalur request API
# berarti kontainer API memuat seluruh pustaka bot hanya demi lima baris peta ini.
_PAYMENT_LABEL_ID = {
    "Promise to Pay": "Janji Bayar",
    "Paid": "Lunas",
    "Refused": "Menolak",
    "Not Home": "Tidak di Rumah",
    "Partial Payment": "Bayar Sebagian",
}


def notify_managers_of_report(report_id: str):
    """Kabari manajer & admin bahwa satu kunjungan lapangan sudah dilaporkan.

    Membuka sesinya sendiri (pola external.geocode_targets): dijalankan sebagai
    BackgroundTask setelah respons terkirim, jadi sesi request-nya sudah ditutup.
    """
    from ..database import SessionLocal
    from ..notifications import send_telegram_notification
    from ..lib.format import format_currency_python

    db = SessionLocal()
    try:
        row = (
            db.query(DbReport, DbTarget, DbUser)
            .join(DbTarget, DbReport.target_id == DbTarget.id)
            .join(DbUser, DbReport.officer_id == DbUser.id)
            .filter(DbReport.id == report_id)
            .first()
        )
        if not row:
            return
        report, target, officer = row

        status_value = report.payment_status.value if hasattr(report.payment_status, "value") else report.payment_status
        notes = (report.notes or "").strip()
        if len(notes) > 200:
            notes = notes[:200].rstrip() + "…"

        message = (
            "*Kunjungan Selesai*\n\n"
            f"Nasabah: *{target.customer_name}*\n"
            f"Petugas: {officer.name}\n"
            f"Hasil: *{_PAYMENT_LABEL_ID.get(status_value, status_value)}*\n"
            f"Tagihan: {format_currency_python(target.amount_due)}\n"
            f"Alamat: {target.address}\n"
            f"Catatan: {notes or '-'}"
        )

        # Penerima disaring dengan `!= officer`, BUKAN `== manager`. Setelah peran
        # admin dipisah, organisasi bisa saja hanya punya akun admin — filter
        # `== manager` akan mengirim nol notifikasi tanpa satu pun galat.
        recipients = (
            db.query(DbUser)
            .filter(
                DbUser.role != UserRole.officer,
                DbUser.active.is_(True),
                DbUser.telegram_id.isnot(None),
            )
            .all()
        )
        for recipient in recipients:
            ok = send_telegram_notification(recipient.telegram_id, message)
            db.add(DbNotificationLog(
                recipient_id=recipient.id,
                message=f"Kunjungan selesai: {target.customer_name}",
                success="true" if ok else "false",
            ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Gagal mengirim notifikasi kunjungan selesai")
    finally:
        db.close()

def get_current_officer(x_telegram_auth: str = Header(None), db: Session = Depends(get_db)):
    """Dependency to extract and validate officer from Telegram header"""
    if not x_telegram_auth:
        raise HTTPException(status_code=401, detail="Missing Telegram Auth Header")
        
    # 1. Validasi Kriptografi (Anti-Spoofing)
    is_valid = validate_telegram_data(x_telegram_auth)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid Telegram Signature. Potential Spoofing Attack.")

    # 2. Ekstrak Data User setelah dipastikan valid
    parsed_data = dict(parse_qsl(x_telegram_auth))
    user_data_str = parsed_data.get("user")
    
    if not user_data_str:
        raise HTTPException(status_code=400, detail="User data not found in Telegram payload")
        
    try:
        user_data = json.loads(user_data_str)
        telegram_id = str(user_data.get("id"))
    except (json.JSONDecodeError, KeyError, TypeError):
        raise HTTPException(status_code=400, detail="Gagal membaca data pengguna Telegram")

    # 3. Cari Officer di Database
    officer = db.query(DbUser).filter(DbUser.telegram_id == telegram_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not registered in C3MR system")
    # Penjaga yang sama seperti di jalur portal (security.py). Tanpa ini, petugas
    # yang sudah diberhentikan tetap membuka Mini App seperti biasa: initData-nya
    # asli, HMAC-nya sah, dan seluruh target lamanya — lengkap dengan nama, alamat,
    # telepon, dan jumlah tagihan nasabah — tetap terbaca sampai admin memindahkan
    # target itu satu per satu.
    if not officer.active:
        raise HTTPException(status_code=403, detail="Akun ini sudah dinonaktifkan")

    return officer

@router.get("/tasks", response_model=List[Target])
async def get_officer_tasks(officer: DbUser = Depends(get_current_officer), db: Session = Depends(get_db)):
    # Terbaru dulu. Tanpa order_by, urutannya adalah urutan baris database — yaitu
    # urutan unggah CSV — yang tidak berarti apa-apa bagi petugas di lapangan.
    return (
        db.query(DbTarget)
        .filter(DbTarget.assigned_officer == officer.id)
        .order_by(DbTarget.created_at.desc())
        .all()
    )

@router.post("/report")
async def submit_report(
    background_tasks: BackgroundTasks,
    target_id: str = Form(...),
    payment_status: str = Form(...),
    notes: Optional[str] = Form(None),
    # Lokasi perangkat petugas saat mengirim. Opsional — petugas bisa menolak izin
    # lokasi, dan laporan tetap harus bisa masuk. Yang tidak mengirim koordinat
    # tampil sebagai "lokasi tidak dibagikan", bukan sebagai kunjungan palsu.
    lat: Optional[float] = Form(None),
    lon: Optional[float] = Form(None),
    photo: UploadFile = File(...),
    officer: DbUser = Depends(get_current_officer),
    db: Session = Depends(get_db)
):
    target = db.query(DbTarget).filter(DbTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
        
    if target.assigned_officer != officer.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this target")

    # payment_status masuk sebagai teks bebas dari form. Nilai di luar daftar dulu
    # lolos sampai ke basis data, lalu meledak sebagai LookupError setiap kali baris
    # itu dibaca kembali — merusak dashboard dan analitik, bukan cuma satu request.
    try:
        payment_status = PaymentStatus(payment_status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Status pembayaran tidak dikenal. Pilih salah satu: {', '.join(s.value for s in PaymentStatus)}",
        )

    ALLOWED_EXT = {"jpg", "jpeg", "png"}
    file_ext = (photo.filename or "").rsplit(".", 1)[-1].lower()
    if file_ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Use: {', '.join(ALLOWED_EXT)}")

    # Satu kunjungan, satu laporan. Ditegakkan lewat UPDATE bersyarat, bukan
    # "baca lalu tulis": ada `await` antara pemeriksaan dan commit, jadi dua request
    # yang datang bersamaan sama-sama membaca in_progress dan sama-sama lolos.
    # Baris ini mengunci barisnya sampai commit di bawah, sehingga request kedua
    # menunggu lalu mendapati syaratnya tak lagi terpenuhi.
    klaim = (
        db.query(DbTarget)
        .filter(DbTarget.id == target_id, DbTarget.status != TargetStatus.completed)
        .update({"status": TargetStatus.completed}, synchronize_session=False)
    )
    if not klaim:
        raise HTTPException(status_code=409, detail="Target ini sudah dilaporkan selesai")

    # 2. Save Photo locally — dibaca berpotongan dan dihentikan begitu melewati
    # batas. Membaca seluruhnya lebih dulu berarti berkas 3 GB masuk RAM sebelum
    # satu pun pemeriksaan berjalan, dan kontainer mati kena OOM.
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    file_name = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    written = 0
    try:
        with open(file_path, "wb") as buffer:
            while chunk := await photo.read(1024 * 1024):
                written += len(chunk)
                if written > MAX_FILE_SIZE:
                    raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")
                buffer.write(chunk)
    except Exception:
        db.rollback()          # batalkan klaim — targetnya harus bisa dilaporkan lagi
        if os.path.exists(file_path):
            os.remove(file_path)
        raise

    # 3. Create Report Record
    # Jarak dihitung SEKALI di sini, bukan tiap kali laporan dibaca: koordinat target
    # bisa berubah kalau alamatnya di-geocode ulang, dan yang ingin dibuktikan adalah
    # seberapa dekat petugas saat itu — bukan menurut data hari ini.
    from ..lib.format import haversine_m
    distance = haversine_m(lat, lon, target.latitude, target.longitude)

    db_report = DbReport(
        target_id=target_id,
        officer_id=officer.id,
        payment_status=payment_status,
        notes=notes,
        photo_url=f"/uploads/{file_name}",  # Local URL
        officer_lat=lat,
        officer_lon=lon,
        distance_m=distance,
    )
    db.add(db_report)

    # Status target sudah disetel oleh UPDATE klaim di atas, dalam transaksi yang
    # sama dengan baris laporan ini — jadi keduanya jadi atau keduanya batal.
    db.commit()

    # Di latar, bukan inline: petugas ada di jaringan seluler dan baru saja
    # mengunggah foto — menahan responsnya selama beberapa panggilan Telegram
    # membuat aplikasi terasa menggantung tepat setelah pekerjaan selesai.
    background_tasks.add_task(notify_managers_of_report, db_report.id)

    return {"message": "Report submitted successfully", "report_id": db_report.id}

@router.post("/comment")
async def submit_comment(
    target_id: str = Form(...),
    message: str = Form(...),
    tag: Optional[str] = Form(None),
    officer: DbUser = Depends(get_current_officer),
    db: Session = Depends(get_db)
):
    target = db.query(DbTarget).filter(DbTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    if target.assigned_officer != officer.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this target")

    comment = DbComment(
        target_id=target_id,
        officer_id=officer.id,
        message=message,
        tag=tag
    )
    db.add(comment)
    db.commit()

    return {"message": "Comment submitted", "comment_id": comment.id}

@router.get("/comments/{target_id}")
async def get_comments(
    target_id: str,
    officer: DbUser = Depends(get_current_officer),
    db: Session = Depends(get_db)
):
    # Dua endpoint tetangga (kirim laporan, kirim komentar) sudah memeriksa
    # penugasan; yang ini dulu menyaring berdasarkan target_id saja. Catatan
    # lapangan memuat keadaan pribadi nasabah, dan id target ikut terkirim ke
    # setiap petugas lewat daftar tugasnya — jadi menebaknya tidak diperlukan.
    target = db.query(DbTarget).filter(DbTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    if target.assigned_officer != officer.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this target")

    comments = (
        db.query(DbComment)
        .filter(DbComment.target_id == target_id)
        .order_by(DbComment.created_at.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "message": c.message,
            "tag": c.tag,
            "created_at": utc_iso(c.created_at)
        }
        for c in comments
    ]
