from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .auth import secret
from .routers.api import router


@asynccontextmanager
async def lifespan(app):
    secret()
    yield


app = FastAPI(title="Rita & Jean Finance", version="0.1.0", lifespan=lifespan)
app.include_router(router)
static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static), name="static")


@app.middleware("http")
async def security_headers(request, call_next):
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
