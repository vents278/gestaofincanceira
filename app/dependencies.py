from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .auth import Identity, current_identity
from .database import get_db
from .models import Membership, User


@dataclass
class UserContext:
    id: UUID
    family_id: UUID
    name: str
    email: str
    role: str
    active: bool = True


def family_members(db, family_id):
    rows = db.execute(
        select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.family_id == family_id, Membership.active.is_(True))
    )
    return [UserContext(u.id, m.family_id, u.name, u.email, m.role) for u, m in rows]


def current_user(
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db)
):
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == identity.id, Membership.active.is_(True)
        )
    )
    if not membership:
        # An inactive membership must never be turned back on by bootstrap.
        db.execute(
            text("select public.bootstrap_family(:name,:code)"),
            {
                "name": identity.metadata.get("family_name"),
                "code": identity.metadata.get("invitation_code"),
            },
        )
        db.commit()
        membership = db.scalar(
            select(Membership).where(
                Membership.user_id == identity.id, Membership.active.is_(True)
            )
        )
    if not membership:
        raise HTTPException(403, "Integrante inativo ou grupo indisponível")
    profile = db.get(User, identity.id)
    return UserContext(
        profile.id, membership.family_id, profile.name, profile.email, membership.role
    )


def admin(user: UserContext = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Acesso restrito ao administrador")
    return user
