from pathlib import Path
from urllib.parse import quote
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import Identity, current_identity
from ..config import settings
from ..database import get_db
from ..dependencies import UserContext, current_user
from ..models import Attachment, Expense
from .api import commit, editable

router = APIRouter(prefix="/api", tags=["Supabase Storage"])
LIMIT = 5 * 1024 * 1024
TYPES = {
    "application/pdf": ("pdf", b"%PDF-"),
    "image/png": ("png", b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": ("jpg", b"\xff\xd8\xff"),
}


def storage_request(method, path, identity, **kwargs):
    config = settings()
    try:
        response = httpx.request(
            method,
            config.supabase_url + "/storage/v1/" + path,
            headers={
                "apikey": config.publishable_key,
                "Authorization": "Bearer " + identity.access_token,
                **kwargs.pop("headers", {}),
            },
            timeout=30,
            **kwargs,
        )
    except httpx.HTTPError:
        raise HTTPException(503, "Supabase Storage indisponível") from None
    if not response.is_success:
        raise HTTPException(
            403 if response.status_code in (400, 401, 403, 404) else 503,
            "Arquivo indisponível ou acesso negado pelo Storage",
        )
    return response


@router.post("/entries/{id}/attachments", status_code=201)
async def upload(
    id: UUID,
    request: Request,
    filename: str = Query(min_length=1, max_length=200),
    identity: Identity = Depends(current_identity),
    user: UserContext = Depends(current_user),
    db: Session = Depends(get_db),
):
    expense = editable(db, user, id)
    if not isinstance(expense, Expense):
        raise HTTPException(422, "Comprovantes são vinculados a despesas")
    mime = request.headers.get("content-type", "").split(";")[0]
    if mime not in TYPES:
        raise HTTPException(415, "Envie PDF, PNG ou JPEG")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > LIMIT:
            raise HTTPException(413, "Limite de 5 MB por arquivo")
    extension, signature = TYPES[mime]
    if not body.startswith(signature):
        raise HTTPException(415, "O conteúdo não corresponde ao tipo informado")
    object_path = f"{user.id}/{id}/{uuid4()}.{extension}"
    # The caller's JWT is used for Storage too. A service key is never required.
    storage_request(
        "POST",
        "object/comprovantes/" + object_path,
        identity,
        content=bytes(body),
        headers={"Content-Type": mime, "x-upsert": "false"},
    )
    item = Attachment(
        family_id=user.family_id,
        owner_id=user.id,
        expense_id=id,
        object_path=object_path,
        filename=Path(filename.replace("\\", "/")).name,
        content_type=mime,
    )
    try:
        db.add(item)
        commit(db)
    except Exception:
        # Best effort: orphan objects remain private and can be reconciled later.
        try:
            storage_request(
                "DELETE",
                "object/comprovantes",
                identity,
                json={"prefixes": [object_path]},
            )
        except HTTPException:
            pass
        raise
    return {"id": item.id, "filename": item.filename}


@router.get("/entries/{id}/attachments")
def attachments(
    id: UUID, user: UserContext = Depends(current_user), db: Session = Depends(get_db)
):
    if not db.get(Expense, id):
        raise HTTPException(404, "Despesa não encontrada")
    return [
        {"id": a.id, "filename": a.filename, "content_type": a.content_type}
        for a in db.scalars(select(Attachment).where(Attachment.expense_id == id))
    ]


@router.get("/attachments/{id}")
def download(
    id: UUID,
    identity: Identity = Depends(current_identity),
    user: UserContext = Depends(current_user),
    db: Session = Depends(get_db),
):
    item = db.get(Attachment, id)
    if not item:
        raise HTTPException(404, "Comprovante não encontrado")
    result = storage_request(
        "GET", "object/authenticated/comprovantes/" + item.object_path, identity
    )
    return Response(
        content=result.content,
        media_type=item.content_type,
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''"
            + quote(item.filename, safe=""),
            "Cache-Control": "no-store",
        },
    )
