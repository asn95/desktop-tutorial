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
JWT_EXPIRY_HOURS = 24

TELEGRAM_AUTH_MAX_AGE = 300  # 5 minutes — reject replayed initData older than this

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

def get_current_manager(authorization: str = None):
    """FastAPI dependency: extract and validate JWT from Authorization header."""
    from fastapi import Header, HTTPException
    def _dep(authorization: str = Header(None, alias="Authorization")):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid token")
        token = authorization.split(" ", 1)[1]
        try:
            payload = decode_access_token(token)
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    return _dep

# Reusable dependency instance
require_auth = get_current_manager()

def _require_manager_dep(authorization: str = None):
    """FastAPI dependency: require JWT with manager role."""
    from fastapi import Header, HTTPException
    def _dep(authorization: str = Header(None, alias="Authorization")):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid token")
        token = authorization.split(" ", 1)[1]
        try:
            payload = decode_access_token(token)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        if payload.get("role") != "manager":
            raise HTTPException(status_code=403, detail="Manager role required")
        return payload
    return _dep

require_manager = _require_manager_dep()
