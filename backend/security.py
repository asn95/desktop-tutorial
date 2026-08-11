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
        # Gagal-tertutup, tanpa pengecualian. Dulu ada cabang "kalau DEBUG=true dan
        # token kosong, izinkan" — satu flag env salah membuat siapa pun bisa
        # menyamar sebagai petugas mana pun hanya dengan menebak Telegram ID-nya,
        # dan ID itu dicetak terang-terangan oleh bot ke layar tiap petugas.
        # Untuk dev, pakai token bot sungguhan; verifikasi kriptografi tidak boleh
        # punya jalur "kalau tidak dikonfigurasi, lewati saja".
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

def _require_roles(*allowed: str):
    """Dependency FastAPI: JWT sah + peran diverifikasi ulang ke basis data.

    Klaim `role` di dalam token TIDAK dipercaya sendirian: token yang dicetak saat
    akun masih manajer tetap sah secara kriptografis sampai kedaluwarsa meskipun
    akunnya sudah dihapus atau diturunkan. Karena itu penggunanya dimuat ulang
    lewat `sub` setiap request, dan basis data yang jadi sumber kebenaran.

    Tanpa argumen: cukup terautentikasi. Dengan argumen: perannya harus termasuk.
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
        try:
            payload = decode_access_token(authorization.split(" ", 1)[1])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = payload.get("sub")
        user = db.query(DbUser).filter(DbUser.id == user_id).first() if user_id else None
        # Pemilik token WAJIB masih ada. Sebelumnya pemeriksaan ini ditulis
        # `if user and ...`, sehingga pengguna yang akunnya sudah DIHAPUS justru
        # lolos: user bernilai None, syaratnya salah, requestnya diteruskan.
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        if _token_issued_before_password_change(payload, user):
            raise HTTPException(status_code=401, detail="Sesi berakhir karena kata sandi diubah. Silakan login ulang.")
        # Menonaktifkan akun harus MENCABUT akses, bukan sekadar menyembunyikannya
        # dari daftar penugasan. Tanpa baris ini, manajer yang baru dinonaktifkan
        # tetap bisa memakai token lamanya sampai kedaluwarsa — termasuk mengekspor
        # seluruh data nasabah ke CSV.
        if not user.active:
            raise HTTPException(status_code=401, detail="Akun ini sudah dinonaktifkan.")
        role = user.role.value if hasattr(user.role, "value") else user.role
        if allowed and role not in allowed:
            raise HTTPException(status_code=403, detail=f"Butuh peran: {' atau '.join(allowed)}")
        return payload
    return _dep


require_auth    = _require_roles()                        # siapa pun yang terautentikasi
require_portal  = _require_roles("manager", "admin")      # halaman yang dipakai keduanya
require_manager = _require_roles("manager")               # kerja operasional
require_admin   = _require_roles("admin")                 # kelola akun, audit, pemeliharaan
