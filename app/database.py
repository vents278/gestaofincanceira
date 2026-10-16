import json
from functools import lru_cache

from fastapi import Depends, HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import DeclarativeBase, Session

from .auth import Identity, current_identity
from .config import settings


class Base(DeclarativeBase):
    pass


class FinanceSession(Session):
    """Every transaction is scoped, including transactions started after commit."""


@event.listens_for(FinanceSession, "after_begin")
def scope_transaction(session, transaction, connection):
    user_id = session.info.get("user_id")
    if user_id is None:
        raise RuntimeError("Uma sessão financeira exige identidade verificada")
    connection.exec_driver_sql("SET LOCAL ROLE authenticated")
    connection.exec_driver_sql(
        "SELECT set_config('request.jwt.claims', %s, true)",
        (json.dumps({"sub": str(user_id), "role": "authenticated"}),),
    )


@lru_cache
def get_engine():
    return create_engine(
        settings().database_url, pool_pre_ping=True, hide_parameters=True
    )


def get_db(identity: Identity = Depends(current_identity)):
    try:
        with FinanceSession(bind=get_engine(), info={"user_id": identity.id}) as db:
            yield db
    except DBAPIError as error:
        code = getattr(error.orig, "sqlstate", None)
        if code in ("23503", "23505", "23514", "22023"):
            raise HTTPException(
                409,
                "Operação incompatível com vínculos, convite ou histórico existente",
            ) from None
        if code == "42501":
            raise HTTPException(
                403, "Operação bloqueada pelas políticas de acesso do grupo"
            ) from None
        raise HTTPException(503, "Banco indisponível ou migrações pendentes") from None
