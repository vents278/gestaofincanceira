from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

bearer = HTTPBearer(auto_error=False)


@dataclass
class Identity:
    id: UUID
    email: str
    metadata: dict
    access_token: str


def auth_request(method, path, *, token=None, data=None):
    config = settings()
    headers = {"apikey": config.publishable_key}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        response = httpx.request(
            method,
            config.supabase_url + "/auth/v1/" + path,
            headers=headers,
            json=data,
            timeout=15,
        )
    except httpx.HTTPError:
        raise HTTPException(503, "Supabase Auth indisponível") from None
    if not response.is_success:
        if response.status_code == 429:
            raise HTTPException(
                429, "Muitas tentativas. Aguarde antes de tentar novamente."
            )
        if response.status_code >= 500:
            raise HTTPException(503, "Supabase Auth indisponível")
        raise HTTPException(
            401 if path.startswith(("token", "user", "logout")) else 400,
            "Autenticação não concluída. Verifique os dados e a confirmação do e-mail.",
        )
    return response.json() if response.content else {}


def verify_access(raw):
    # Auth /user validates signature, issuer, expiry and session with the project.
    # Never trust jwt.decode(..., verify_signature=False) or browser-supplied IDs.
    data = auth_request("GET", "user", token=raw)
    try:
        return Identity(
            UUID(data["id"]), data["email"], data.get("user_metadata") or {}, raw
        )
    except (KeyError, TypeError, ValueError):
        raise HTTPException(401, "Identidade Supabase inválida") from None


def current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Autenticação necessária")
    return verify_access(credentials.credentials)
