import os
import hashlib
import hmac
from urllib.parse import parse_qsl

import jwt
import bcrypt
from datetime import datetime, timedelta, timezone

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET environment variable is required. Set it before starting the server.")
JWT_ALGORITHM = "HS256"
# Shortened from 24h: a stolen/stale token is now valid for at most 4h. Privileged
# (manager) endpoints additionally re-verify the user + role against the DB on each
# request (see require_manager) so revoked/demoted accounts lose access immediately.
JWT_EXPIRY_HOURS = 4

TELEGRAM_AUTH_MAX_AGE = 300  # 5 minutes — reject replayed initData older than this

# Satu kebijakan panjang kata sandi untuk seluruh akun portal (pembuatan akun,
# ganti sandi, reset lewat Telegram). Bootstrap /seed-admin tetap lebih ketat (12).
MIN_PASSWORD_LENGTH = 8

def validate_telegram_data(init_data: str) -> bool:
    """
    Memvalidasi integritas data yang dikirim dari Telegram Mini App
    menggunakan algoritma HMAC-SHA256, termasuk freshness check pada auth_date.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        debug = os.environ.get("DEBUG", "false").lower() == "true"
        if debug:
            print("WARNING: TELEGRAM_BOT_TOKEN not set. Skipping validation (DEBUG mode).")
            return True
        return False

    # 1. Parse data menjadi dictionary
    parsed_data = dict(parse_qsl(init_data))

    # 2. Ambil hash signature dari Telegram
    if "hash" not in parsed_data:
        return False

    telegram_hash = parsed_data.pop("hash")

    # 3. Freshness check — reject replayed initData older than 5 minutes
    auth_date_str = parsed_data.get("auth_date")
    if auth_date_str:
        try:
            auth_date = int(auth_date_str)
            now = int(datetime.now(timezone.utc).timestamp())
            if now - auth_date > TELEGRAM_AUTH_MAX_AGE:
                return False
        except (ValueError, TypeError):
            return False

    # 4. Urutkan sisa data berdasarkan abjad (Key)
    data_check_arr = []
    for key, value in sorted(parsed_data.items()):
        data_check_arr.append(f"{key}={value}")

    # 5. Gabungkan menjadi satu string (Data Check String)
    data_check_string = "\n".join(data_check_arr)

    # 6. Buat Secret Key (Kunci Rahasia) dari Bot Token
    # Secret key = HMAC_SHA256(bot_token, "WebAppData")
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()

    # 7. Hitung HMAC-SHA256 dari Data Check String menggunakan Secret Key
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    # 8. Bandingkan hash yang kita hitung dengan hash dari Telegram
    # Menggunakan compare_digest untuk mencegah serangan Timing Attack
    return hmac.compare_digest(calculated_hash, telegram_hash)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_access_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

def _token_issued_before_password_change(payload: dict, user) -> bool:
    """True jika token terbit SEBELUM kata sandi terakhir diubah → token harus ditolak.

    Dengan begitu setiap penggantian kata sandi otomatis membatalkan semua token lama
    (termasuk sesi yang sedang berjalan), sehingga pengguna wajib login ulang.
    """
    changed_at = getattr(user, "password_changed_at", None)
    if not changed_at:
        return False
    iat = payload.get("iat")
    if iat is None:
        return True  # token tanpa iat (skema lama) diperlakukan sebagai kedaluwarsa
    if changed_at.tzinfo is None:
        changed_at = changed_at.replace(tzinfo=timezone.utc)
    return int(iat) < int(changed_at.timestamp())

def get_current_manager(authorization: str = None):
    """FastAPI dependency: extract and validate JWT from Authorization header.

    Selain memeriksa tanda tangan JWT, token juga ditolak bila terbit sebelum kata
    sandi pemiliknya terakhir diubah — memaksa login ulang setelah ganti kata sandi.
    """
    from fastapi import Header, HTTPException, Depends
    from sqlalchemy.orm import Session
    from .database import get_db
    from .models import DbUser

    def _dep(
        authorization: str = Header(None, alias="Authorization"),
        db: Session = Depends(get_db),
    ):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid token")
        token = authorization.split(" ", 1)[1]
        try:
            payload = decode_access_token(token)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = payload.get("sub")
        user = db.query(DbUser).filter(DbUser.id == user_id).first() if user_id else None
        # Pemilik token WAJIB masih ada. Sebelumnya pemeriksaan di bawah ditulis
        # `if user and ...`, sehingga pengguna yang akunnya sudah DIHAPUS justru lolos:
        # user bernilai None, syaratnya salah, requestnya diteruskan. Akibatnya token
        # milik akun terhapus tetap bisa dipakai sampai kedaluwarsa sendiri.
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        if _token_issued_before_password_change(payload, user):
            raise HTTPException(status_code=401, detail="Sesi berakhir karena kata sandi diubah. Silakan login ulang.")
        return payload
    return _dep

# Reusable dependency instance
require_auth = get_current_manager()

def _require_manager_dep(authorization: str = None):
    """FastAPI dependency: require a valid JWT AND re-verify manager status in the DB.

    The JWT's role claim is not trusted on its own: a token minted while the account was
    a manager stays cryptographically valid until expiry even if the account was later
    deleted or demoted. So on every privileged request we re-load the user by `sub` and
    confirm they still exist and still hold the manager role; the DB is the source of truth.
    """
    from fastapi import Header, HTTPException, Depends
    from sqlalchemy.orm import Session
    from .database import get_db
    from .models import DbUser

    def _dep(
        authorization: str = Header(None, alias="Authorization"),
        db: Session = Depends(get_db),
    ):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid token")
        token = authorization.split(" ", 1)[1]
        try:
            payload = decode_access_token(token)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = payload.get("sub")
        user = db.query(DbUser).filter(DbUser.id == user_id).first() if user_id else None
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        if _token_issued_before_password_change(payload, user):
            raise HTTPException(status_code=401, detail="Sesi berakhir karena kata sandi diubah. Silakan login ulang.")
        # Compare against the live DB role, not the (possibly stale) JWT claim.
        role = user.role.value if hasattr(user.role, "value") else user.role
        # admin ikut diterima: peran ini dipisah dari manager untuk memisahkan menu,
        # bukan untuk mencabut akses. Kalau di sini tetap "manager" saja, setiap
        # endpoint yang memakai require_manager langsung 403 bagi admin.
        if role not in ("manager", "admin"):
            raise HTTPException(status_code=403, detail="Manager role required")
        return payload
    return _dep

require_manager = _require_manager_dep()


def _require_admin_dep():
    """Sama seperti _require_manager_dep, tapi hanya menerima peran admin.

    Sengaja disalin, bukan diabstraksi: dua penjaga yang tampak mirip tapi berbeda
    satu baris lebih aman dibaca daripada satu fungsi berparameter yang salah
    dipanggil diam-diam meloloskan peran yang tidak diinginkan.
    """
    from fastapi import Header, HTTPException, Depends
    from sqlalchemy.orm import Session
    from .database import get_db
    from .models import DbUser

    def _dep(
        authorization: str = Header(None, alias="Authorization"),
        db: Session = Depends(get_db),
    ):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid token")
        token = authorization.split(" ", 1)[1]
        try:
            payload = decode_access_token(token)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = payload.get("sub")
        user = db.query(DbUser).filter(DbUser.id == user_id).first() if user_id else None
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        if _token_issued_before_password_change(payload, user):
            raise HTTPException(status_code=401, detail="Sesi berakhir karena kata sandi diubah. Silakan login ulang.")
        role = user.role.value if hasattr(user.role, "value") else user.role
        if role != "admin":
            raise HTTPException(status_code=403, detail="Butuh peran admin")
        return payload
    return _dep

require_admin = _require_admin_dep()
