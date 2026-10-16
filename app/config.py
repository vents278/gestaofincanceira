import base64
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

from sqlalchemy.engine import make_url


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    publishable_key: str
    database_url: str
    app_url: str

    @property
    def secure_cookie(self):
        return self.app_url.startswith("https://")


@lru_cache
def settings():
    names = ["SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "DATABASE_URL", "APP_URL"]
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        raise RuntimeError("Configure as variáveis: " + ", ".join(missing))
    url = os.environ["SUPABASE_URL"].rstrip("/")
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.path
    ):
        raise RuntimeError("SUPABASE_URL deve ser uma origem HTTPS")
    key = os.environ["SUPABASE_PUBLISHABLE_KEY"]
    if key.startswith("sb_secret_"):
        raise RuntimeError("Use chave publicável/anon, nunca service_role")
    if key.count(".") == 2:
        try:
            role = json.loads(base64.urlsafe_b64decode(key.split(".")[1] + "===")).get(
                "role"
            )
        except (ValueError, KeyError):
            raise RuntimeError("Chave anon inválida")
        if role != "anon":
            raise RuntimeError("Use chave publicável/anon, nunca service_role")
    db = os.environ["DATABASE_URL"]
    if not db.startswith("postgresql+psycopg://"):
        raise RuntimeError(
            "DATABASE_URL deve usar postgresql+psycopg://; SQLite não é suportado"
        )
    parsed_db = make_url(db)
    if (
        parsed_db.host not in (None, "localhost", "127.0.0.1", "::1")
        and parsed_db.query.get("sslmode") != "verify-full"
    ):
        raise RuntimeError(
            "PostgreSQL remoto exige sslmode=verify-full e certificado raiz confiável"
        )
    app = os.environ["APP_URL"].rstrip("/")
    if (
        urlparse(app).scheme not in ("http", "https")
        or not urlparse(app).netloc
        or urlparse(app).username
        or urlparse(app).path
        or urlparse(app).query
        or urlparse(app).fragment
    ):
        raise RuntimeError("APP_URL inválida")
    if urlparse(app).scheme == "http" and urlparse(app).hostname not in (
        "localhost",
        "127.0.0.1",
        "testserver",
    ):
        raise RuntimeError("APP_URL pública deve usar HTTPS")
    return Settings(url, key, db, app)
