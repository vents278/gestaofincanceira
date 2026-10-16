from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials

from ..auth import Identity, auth_request, bearer, current_identity, verify_access
from ..config import settings
from ..schemas import Callback, Login, PasswordUpdate, Recovery, Register

router = APIRouter(prefix="/api/auth", tags=["Supabase Auth"])
COOKIE = "finance_refresh"


def session_response(data, response):
    if not data.get("access_token") or not data.get("refresh_token"):
        return {"confirmation_required": True}
    response.set_cookie(
        COOKIE,
        data["refresh_token"],
        httponly=True,
        secure=settings().secure_cookie,
        samesite="strict",
        path="/api/auth",
        max_age=60 * 60 * 24 * 30,
    )
    return {
        "access_token": data["access_token"],
        "token_type": "bearer",
        "expires_in": data.get("expires_in", 3600),
    }


@router.post("/register", status_code=201)
def register(data: Register, response: Response):
    result = auth_request(
        "POST",
        "signup",
        data={
            "email": str(data.email),
            "password": data.password,
            "data": {
                "name": data.name,
                "family_name": data.family_name,
                "invitation_code": data.invitation_code,
            },
        },
    )
    return session_response(result, response)


@router.post("/login")
def login(data: Login, response: Response):
    result = auth_request(
        "POST",
        "token?grant_type=password",
        data={"email": str(data.email), "password": data.password},
    )
    return session_response(result, response)


@router.post("/refresh")
def refresh(response: Response, finance_refresh: str | None = Cookie(default=None)):
    if not finance_refresh:
        raise HTTPException(401, "Sessão não encontrada")
    data = auth_request(
        "POST",
        "token?grant_type=refresh_token",
        data={"refresh_token": finance_refresh},
    )
    return session_response(data, response)


@router.post("/callback")
def callback(data: Callback, response: Response):
    identity = verify_access(data.access_token)
    refreshed = auth_request(
        "POST",
        "token?grant_type=refresh_token",
        data={"refresh_token": data.refresh_token},
    )
    if str(identity.id) != refreshed.get("user", {}).get("id"):
        raise HTTPException(401, "Sessões incompatíveis")
    return session_response(refreshed, response)


@router.post("/logout", status_code=204)
def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    response = Response(status_code=204)
    if credentials:
        try:
            auth_request("POST", "logout?scope=local", token=credentials.credentials)
        except HTTPException as error:
            if error.status_code >= 500:
                response.status_code = 503
    response.delete_cookie(
        COOKIE, path="/api/auth", secure=settings().secure_cookie, samesite="strict"
    )
    return response


@router.post("/recover")
def recover(data: Recovery):
    auth_request(
        "POST",
        "recover?redirect_to=" + settings().app_url + "/",
        data={"email": str(data.email)},
    )
    return {
        "message": "Se houver uma conta elegível, enviaremos as instruções por e-mail."
    }


@router.put("/password")
def password(data: PasswordUpdate, identity: Identity = Depends(current_identity)):
    auth_request(
        "PUT", "user", token=identity.access_token, data={"password": data.password}
    )
    return {"message": "Senha atualizada"}
