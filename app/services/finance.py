from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException
from sqlalchemy import or_, select

from ..models import Account, Category, Entry, User

ZERO = Decimal("0.00")


def money(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def visible(db, user):
    return list(
        db.scalars(
            select(Entry).where(
                Entry.family_id == user.family_id,
                Entry.cancelled.is_(False),
                or_(Entry.private.is_(False), Entry.owner_id == user.id),
            )
        )
    )


def related(db, model, id, family):
    obj = db.get(model, id)
    if not obj or obj.family_id != family:
        raise HTTPException(404, "Registro não encontrado neste grupo")
    return obj


def validate_entry(db, user, data):
    for model, id in [
        (User, data.owner_id),
        (User, data.payer_id),
        (Account, data.account_id),
        (Category, data.category_id),
    ]:
        related(db, model, id, user.family_id)
    if user.role != "admin" and data.owner_id != user.id:
        raise HTTPException(403, "Integrantes só registram seus próprios lançamentos")
    if data.private and data.owner_id != user.id:
        raise HTTPException(
            403, "Despesa privada deve pertencer ao usuário autenticado"
        )
    if related(db, Category, data.category_id, user.family_id).kind != data.kind:
        raise HTTPException(422, "Categoria incompatível com lançamento")
    if data.shared:
        members = list(
            db.scalars(
                select(User).where(
                    User.family_id == user.family_id, User.active.is_(True)
                )
            )
        )
        if len(members) != 2:
            raise HTTPException(422, "Divisão exige exatamente dois integrantes ativos")
        if data.split_mode == "equal":
            data.share_percent = Decimal("50")
        elif data.split_mode == "proportional":
            incomes = [
                e
                for e in visible(db, user)
                if e.kind == "income"
                and e.due_date.strftime("%Y-%m") == data.due_date.strftime("%Y-%m")
            ]
            total = sum((e.amount for e in incomes), ZERO)
            own = sum((e.amount for e in incomes if e.owner_id == data.owner_id), ZERO)
            if total <= 0:
                raise HTTPException(
                    422, "Cadastre receitas visíveis no mês para divisão proporcional"
                )
            data.share_percent = money(own / total * 100)


def splits(entries, members):
    net = {m.id: ZERO for m in members}
    for e in entries:
        if not e.shared or not e.settled_date:
            continue
        other = next((m.id for m in members if m.id != e.owner_id), None)
        if other is None:
            continue
        own = money(e.amount * e.share_percent / 100)
        net[e.owner_id] -= own
        net[other] -= e.amount - own
        net[e.payer_id] += e.amount
    return [{"user_id": k, "net": money(v)} for k, v in net.items()]
