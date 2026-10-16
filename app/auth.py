import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

passwords = PasswordHash.recommended()
bearer = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def secret():
    value = os.getenv("JWT_SECRET", "")
    if len(value) < 32:
        raise RuntimeError(
            "Configure JWT_SECRET com pelo menos 32 caracteres aleatórios"
        )
    return value


def token(user):
    return jwt.encode(
        {"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(hours=8)},
        secret(),
        algorithm="HS256",
    )


def current_user(raw: str = Depends(bearer), db: Session = Depends(get_db)):
    try:
        data = jwt.decode(
            raw, secret(), algorithms=["HS256"], options={"require": ["exp", "sub"]}
        )
        user = db.get(User, int(data["sub"]))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(401, "Sessão inválida ou expirada")
    if not user or not user.active:
        raise HTTPException(401, "Usuário indisponível")
    return user


def admin(user: User = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Acesso restrito ao administrador")
    return user
