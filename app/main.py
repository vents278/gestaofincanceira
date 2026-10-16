from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers.api import router
from .routers.auth import router as auth_router
from .routers.storage import router as storage_router


@asynccontextmanager
async def lifespan(app):
    settings()
    yield


app = FastAPI(title="Rita & Jean Finance", version="0.2.0", lifespan=lifespan)
app.include_router(router)
app.include_router(auth_router)
app.include_router(storage_router)
static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static), name="static")


@app.middleware("http")
async def security_headers(request, call_next):
    if request.method in ("POST", "PUT", "DELETE") and request.headers.get(
        "origin"
    ) not in (None, settings().app_url):
        from fastapi.responses import JSONResponse

        return JSONResponse({"detail": "Origem não permitida"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    )
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(static / "index.html")


@app.get("/health/ready")
def ready():
    from fastapi import HTTPException
    from sqlalchemy import text

    from .database import get_engine

    try:
        with get_engine().connect() as conn:
            conn.execute(text("select id from public.receitas limit 0"))
        return {"status": "ready", "database": "postgresql"}
    except Exception:
        raise HTTPException(
            503, "Conexão PostgreSQL ou migrações indisponíveis"
        ) from None
