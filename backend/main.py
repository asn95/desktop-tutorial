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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import all models so Base.metadata knows about them
from .models import DbUser, DbTarget, DbReport, DbComment, DbAuditLog, DbNotificationLog  # noqa: F401

# Create all tables on startup
Base.metadata.create_all(bind=engine)

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
_default_origins = "https://c3mr-app-production.up.railway.app"
if os.environ.get("DEBUG", "false").lower() == "true":
    _default_origins += ",http://localhost:5173,http://localhost:3000"
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", _default_origins).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
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

@app.get("/api")
async def api_root():
    return {"message": "Welcome to C3MR API"}

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
