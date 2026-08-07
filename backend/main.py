from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
import os, traceback, logging
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time
from .database import engine, Base
from fastapi.staticfiles import StaticFiles
from .routers import targets, dashboard, auth, users, analytics, officer, audit
from .maintenance import maintenance_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import all models so Base.metadata knows about them
from .models import DbUser, DbTarget, DbReport, DbComment, DbAuditLog, DbNotificationLog  # noqa: F401

# Create all tables on startup
Base.metadata.create_all(bind=engine)

# Lightweight in-place migration: create_all does not alter existing tables,
# so add the 'period' column ourselves and backfill legacy rows from created_at.
def _migrate_target_period():
    from sqlalchemy import inspect, text
    from .database import SessionLocal
    from datetime import datetime, timezone

    cols = {c["name"] for c in inspect(engine).get_columns("targets")}
    if "period" not in cols:
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE targets ADD COLUMN period VARCHAR"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_targets_period ON targets (period)"))
        except Exception:
            logger.exception("Gagal menambahkan kolom period (mungkin sudah ada)")

    db = SessionLocal()
    try:
        legacy = db.query(DbTarget).filter(DbTarget.period.is_(None)).all()
        for t in legacy:
            base = t.created_at or datetime.now(timezone.utc)
            t.period = base.strftime("%Y-%m")
        if legacy:
            db.commit()
            logger.info(f"Migrasi period: {len(legacy)} target lama diberi label periode")
    except Exception:
        db.rollback()
        logger.exception("Gagal backfill period untuk target lama")
    finally:
        db.close()

def _migrate_target_geo():
    """Tambah kolom koordinat (hasil geocoding Nominatim) ke tabel targets lama."""
    from sqlalchemy import inspect, text

    cols = {c["name"] for c in inspect(engine).get_columns("targets")}
    for col in ("latitude", "longitude"):
        if col not in cols:
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE targets ADD COLUMN {col} FLOAT"))
            except Exception:
                logger.exception(f"Gagal menambahkan kolom {col} (mungkin sudah ada)")


def _migrate_user_password_changed_at():
    """Kolom penanda waktu ganti kata sandi: token yang terbit sebelum waktu ini
    ditolak (lihat security.py) sehingga user wajib login ulang setelah ganti sandi."""
    from sqlalchemy import inspect, text

    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    if "password_changed_at" not in cols:
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_changed_at TIMESTAMP"))
        except Exception:
            logger.exception("Gagal menambahkan kolom password_changed_at (mungkin sudah ada)")

# Kolom geo harus ada lebih dulu: backfill period men-SELECT seluruh kolom model
# (termasuk latitude/longitude), jadi urutan sebaliknya gagal di skema lama.
def _migrate_user_active():
    """Kolom soft-delete: petugas nonaktif disembunyikan dari penugasan tapi datanya tetap ada."""
    from sqlalchemy import inspect, text

    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    if "active" not in cols:
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN active BOOLEAN NOT NULL DEFAULT TRUE"))
        except Exception:
            logger.exception("Gagal menambahkan kolom active (mungkin sudah ada)")

def _migrate_user_role_admin():
    """Tambahkan nilai 'admin' ke enum peran.

    Di PostgreSQL peran disimpan sebagai tipe ENUM asli yang dibuat lewat schema.sql
    (create_type=False di models.py), jadi menambah anggota enum di Python saja tidak
    cukup — basis data akan menolak nilainya. ALTER TYPE ... ADD VALUE tidak boleh
    berjalan di dalam transaksi yang kemudian memakai nilai itu, karena itu koneksinya
    dipaksa AUTOCOMMIT.

    SQLite tidak punya tipe enum (SQLAlchemy menyimpannya sebagai VARCHAR + CHECK yang
    hanya dievaluasi saat CREATE TABLE), jadi di dev tidak ada yang perlu dikerjakan.

    Catatan: penambahan nilai enum TIDAK bisa dibatalkan di PostgreSQL. Rollback kode
    aman, tapi baris ber-role='admin' harus dikembalikan lebih dulu.
    """
    from sqlalchemy import text

    if not engine.url.drivername.startswith("postgresql"):
        return
    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'admin'"))
    except Exception:
        logger.exception("Gagal menambahkan nilai enum 'admin' (mungkin sudah ada)")


def _migrate_user_phone():
    """Kolom nomor telepon: petugas menautkan Telegram-nya sendiri lewat nomor ini."""
    from sqlalchemy import inspect, text

    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    if "phone" not in cols:
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone)"))
        except Exception:
            logger.exception("Gagal menambahkan kolom phone (mungkin sudah ada)")


_migrate_target_geo()
_migrate_target_period()
_migrate_user_password_changed_at()
_migrate_user_active()
_migrate_user_role_admin()
_migrate_user_phone()

def _geocode_active_period_backfill():
    """Geocode target periode aktif yang belum punya koordinat, di thread terpisah
    agar startup tidak terblokir (Nominatim dibatasi 1 request/detik)."""
    import threading
    from .database import SessionLocal

    def run():
        db = SessionLocal()
        try:
            periods = [p for (p,) in db.query(DbTarget.period).distinct().all() if p]
            if not periods:
                return
            ids = [
                t.id for t in db.query(DbTarget)
                .filter(DbTarget.period == max(periods), DbTarget.latitude.is_(None))
                .limit(60)
            ]
        finally:
            db.close()
        if ids:
            from .external import geocode_targets
            geocode_targets(ids)

    threading.Thread(target=run, daemon=True, name="geocode-backfill").start()

import sys
if "pytest" not in sys.modules:  # jangan akses jaringan saat unit test
    _geocode_active_period_backfill()

app = FastAPI(title="C3MR API")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {traceback.format_exc()}")
    # Never expose raw exception details to clients — log only
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Serve uploads statically
if not os.path.exists("backend/uploads"):
    os.makedirs("backend/uploads")
app.mount("/api/uploads", StaticFiles(directory="backend/uploads"), name="uploads")

# Serve the Telegram Mini App
app.mount("/officer-app", StaticFiles(directory="mini-app", html=True), name="mini-app")

# Enable CORS — production uses the Railway URL, dev uses localhost
_default_origins = "https://c3mr-app-production-b353.up.railway.app"
if os.environ.get("DEBUG", "false").lower() == "true":
    _default_origins += ",http://localhost:5173,http://localhost:3000"
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", _default_origins).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    # With allow_credentials=True a wildcard is unsafe; restrict to the methods/headers
    # the app actually uses (PATCH+DELETE are used by routers; PUT kept for forward-compat).
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Webview Telegram meng-cache aset mini-app secara agresif sehingga update
        # JS tidak sampai ke petugas; file-nya kecil, paksa revalidasi (304 murah).
        if request.url.path.startswith("/officer-app"):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response

app.add_middleware(SecurityHeadersMiddleware)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = round((time.time() - start) * 1000)
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration}ms)")
        return response

app.add_middleware(RequestLoggingMiddleware)

# Maintenance mode middleware — blocks non-manager API requests when enabled
class MaintenanceMiddleware(BaseHTTPMiddleware):
    # API paths that bypass maintenance mode so managers can still login and toggle it off.
    # Exact-match (with optional trailing slash) so future sibling routes don't inherit the
    # bypass accidentally via a loose startswith() prefix match.
    # Dua jalur reset ikut dibebaskan: tanpa itu admin yang lupa kata sandinya saat
    # mode pemeliharaan menyala terkunci permanen — ia tidak bisa login untuk
    # mematikan pemeliharaan, dan tidak bisa reset karena pemeliharaan menyala.
    BYPASS_PATHS = (
        "/api/auth/login",
        "/api/auth/forgot-password",
        "/api/auth/reset-password",
        "/api/admin/maintenance",
    )

    def _is_bypass(self, path: str) -> bool:
        return any(path == p or path == p + "/" for p in self.BYPASS_PATHS)

    async def dispatch(self, request: Request, call_next):
        if maintenance_state.enabled and request.url.path.startswith("/api"):
            # Allow bypass paths
            if not self._is_bypass(request.url.path):
                # Allow requests with a valid manager JWT through
                from .security import decode_access_token
                auth_header = request.headers.get("authorization", "")
                is_manager = False
                if auth_header.startswith("Bearer "):
                    try:
                        payload = decode_access_token(auth_header.split(" ", 1)[1])
                        is_manager = payload.get("role") in ("manager", "admin")
                    except Exception:
                        pass
                if not is_manager:
                    return JSONResponse(
                        status_code=503,
                        content={"detail": maintenance_state.message},
                    )
        return await call_next(request)

app.add_middleware(MaintenanceMiddleware)

@app.get("/api")
async def api_root():
    return {"message": "Welcome to C3MR API"}

# Maintenance mode endpoints
from .security import require_manager, require_admin
from fastapi import Depends
from pydantic import BaseModel

class MaintenancePayload(BaseModel):
    enabled: bool
    message: str | None = None

@app.get("/api/admin/maintenance")
async def get_maintenance_status():
    return {"enabled": maintenance_state.enabled, "message": maintenance_state.message}

@app.post("/api/admin/maintenance")
async def set_maintenance(payload: MaintenancePayload, _auth: dict = Depends(require_admin)):
    maintenance_state.toggle(payload.enabled, payload.message)
    return {"enabled": maintenance_state.enabled, "message": maintenance_state.message}


# AI Assistant — web access to the Claude (Anthropic) workflow agent (manager-only).
# Reuses the same run_agent() that powers the Telegram /ask command.
from fastapi import HTTPException


class AgentQuery(BaseModel):
    question: str


@app.post("/api/agent/ask")
async def agent_ask(payload: AgentQuery, _auth: dict = Depends(require_manager)):
    question = (payload.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")
    try:
        from .agent import run_agent
        answer = await run_agent(question, actor_id=_auth.get("sub"))
        return {"answer": answer}
    except Exception as e:
        logger.exception("AI agent error")
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(targets.router, prefix="/api/targets", tags=["targets"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(officer.router, prefix="/api/officer", tags=["officer"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])

# Serve frontend build via middleware (does NOT interfere with API routing)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="frontend-assets")

    @app.get("/favicon.svg")
    async def favicon():
        return FileResponse(str(FRONTEND_DIR / "favicon.svg"))

    class SPAMiddleware(BaseHTTPMiddleware):
        """Serve SPA index.html for non-API, non-asset GET requests that return 404."""
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            # Only intercept GET 404s for frontend routes (not API/assets/officer-app)
            if (
                request.method == "GET"
                and response.status_code == 404
                and not request.url.path.startswith(("/api", "/assets", "/officer-app"))
            ):
                return FileResponse(str(FRONTEND_DIR / "index.html"))
            return response

    app.add_middleware(SPAMiddleware)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
