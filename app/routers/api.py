from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import UserContext as User
from ..dependencies import admin, current_user, family_members
from ..models import Account, Category, Entry, Expense, Family, Income
from ..schemas import AccountIn, CategoryIn, EntryIn
from ..services.finance import ZERO, related, splits, validate_entry, visible

router = APIRouter(prefix="/api")


def public_user(u):
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "family_id": u.family_id,
    }


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Já existe um registro com esses dados")


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {**public_user(user), "family_name": db.get(Family, user.family_id).name}


@router.get("/members")
def members(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [public_user(u) for u in family_members(db, user.family_id)]


@router.post("/members/invitations", status_code=201)
def invite(user: User = Depends(admin), db: Session = Depends(get_db)):
    code = db.scalar(text("select public.create_family_invitation()"))
    commit(db)
    return {"invitation_code": code, "expires_in_hours": 48}


@router.get("/accounts")
def accounts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    entries = visible(db, user)
    return [
        {
            "id": a.id,
            "name": a.name,
            "initial_balance": str(a.initial_balance),
            "visible_balance": str(
                a.initial_balance
                + sum(
                    (
                        e.amount if e.kind == "income" else -e.amount
                        for e in entries
                        if e.account_id == a.id and e.settled_date
                    ),
                    ZERO,
                )
            ),
        }
        for a in db.scalars(select(Account).where(Account.family_id == user.family_id))
    ]


@router.post("/accounts", status_code=201)
def add_account(
    data: AccountIn, user: User = Depends(admin), db: Session = Depends(get_db)
):
    obj = Account(**data.model_dump(), family_id=user.family_id)
    db.add(obj)
    db.flush()
    commit(db)
    return {"id": obj.id, "name": obj.name}


@router.get("/categories")
def categories(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [
        {"id": c.id, "name": c.name, "kind": c.kind}
        for c in db.scalars(
            select(Category).where(Category.family_id == user.family_id)
        )
    ]


@router.post("/categories", status_code=201)
def add_category(
    data: CategoryIn, user: User = Depends(admin), db: Session = Depends(get_db)
):
    obj = Category(**data.model_dump(), family_id=user.family_id)
    db.add(obj)
    commit(db)
    return {"id": obj.id, "name": obj.name, "kind": obj.kind}


@router.put("/categories/{id}")
def edit_category(
    id: UUID,
    data: CategoryIn,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    obj = related(db, Category, id, user.family_id)
    if obj.kind != data.kind and (
        db.scalar(select(Income.id).where(Income.category_id == id).limit(1))
        or db.scalar(select(Expense.id).where(Expense.category_id == id).limit(1))
    ):
        raise HTTPException(409, "Categoria em uso não pode mudar de tipo")
    obj.name = data.name
    obj.kind = data.kind
    commit(db)
    return {"id": obj.id, "name": obj.name, "kind": obj.kind}


@router.delete("/categories/{id}", status_code=204)
def delete_category(
    id: UUID, user: User = Depends(admin), db: Session = Depends(get_db)
):
    obj = related(db, Category, id, user.family_id)
    if db.scalar(
        select(Income.id).where(Income.category_id == id).limit(1)
    ) or db.scalar(select(Expense.id).where(Expense.category_id == id).limit(1)):
        raise HTTPException(409, "Categoria possui histórico financeiro")
    db.delete(obj)
    commit(db)
    return Response(status_code=204)


def serialize(e):
    return {
        key: (
            str(getattr(e, key))
            if isinstance(getattr(e, key), Decimal)
            else getattr(e, key)
        )
        for key in [
            "id",
            "description",
            "amount",
            "kind",
            "due_date",
            "settled_date",
            "owner_id",
            "payer_id",
            "account_id",
            "category_id",
            "shared",
            "private",
            "split_mode",
            "share_percent",
            "notes",
        ]
    }


def filtered(db, user, month, owner_id, category_id, account_id):
    return [
        e
        for e in visible(db, user)
        if (not month or e.due_date.strftime("%Y-%m") == month)
        and (not owner_id or e.owner_id == owner_id)
        and (not category_id or e.category_id == category_id)
        and (not account_id or e.account_id == account_id)
    ]


@router.get("/entries")
def entries(
    month: str | None = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    owner_id: UUID | None = None,
    category_id: UUID | None = None,
    account_id: UUID | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return [
        serialize(e)
        for e in sorted(
            filtered(db, user, month, owner_id, category_id, account_id),
            key=lambda e: (e.due_date, e.id),
            reverse=True,
        )
    ]


@router.post("/entries", status_code=201)
def add_entry(
    data: EntryIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    validate_entry(db, user, data)
    model = Income if data.kind == "income" else Expense
    obj = model(**data.model_dump(), family_id=user.family_id)
    db.add(obj)
    db.flush()
    commit(db)
    return serialize(obj)


def editable(db, user, id):
    obj = related(db, Entry, id, user.family_id)
    if (obj.private and obj.owner_id != user.id) or obj.cancelled:
        raise HTTPException(404, "Lançamento não encontrado")
    if user.role != "admin" and obj.owner_id != user.id:
        raise HTTPException(403, "Você só pode alterar seus lançamentos")
    return obj


@router.put("/entries/{id}")
def edit_entry(
    id: UUID,
    data: EntryIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    obj = editable(db, user, id)
    if obj.kind != data.kind:
        raise HTTPException(409, "Para mudar o tipo, cancele o lançamento e crie outro")
    validate_entry(db, user, data)
    for key, value in data.model_dump().items():
        setattr(obj, key, value)
    commit(db)
    return serialize(obj)


@router.delete("/entries/{id}", status_code=204)
def cancel_entry(
    id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    obj = editable(db, user, id)
    obj.cancelled = True
    commit(db)
    return Response(status_code=204)


@router.get("/dashboard")
def dashboard(
    month: str = Query(
        default_factory=lambda: date.today().strftime("%Y-%m"),
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
    ),
    owner_id: UUID | None = None,
    category_id: UUID | None = None,
    account_id: UUID | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    all_entries = visible(db, user)
    selected = filtered(db, user, month, owner_id, category_id, account_id)
    income = sum((e.amount for e in selected if e.kind == "income"), ZERO)
    expense = sum((e.amount for e in selected if e.kind == "expense"), ZERO)
    received = sum(
        (e.amount for e in selected if e.kind == "income" and e.settled_date), ZERO
    )
    paid = sum(
        (e.amount for e in selected if e.kind == "expense" and e.settled_date), ZERO
    )
    pending = sum(
        (e.amount for e in selected if e.kind == "expense" and not e.settled_date), ZERO
    )
    group_members = family_members(db, user.family_id)
    by_category = {}
    for e in selected:
        if e.kind == "expense":
            name = db.get(Category, e.category_id).name
            by_category[name] = by_category.get(name, ZERO) + e.amount
    return jsonable_encoder(
        {
            "month": month,
            "income": income,
            "expense": expense,
            "received": received,
            "paid": paid,
            "pending": pending,
            "savings": received - paid,
            "forecast": income - expense,
            "committed_percent": round(expense / income * 100, 2) if income else None,
            "shared": sum((e.amount for e in selected if e.shared), ZERO),
            "individual": sum(
                (e.amount for e in selected if e.kind == "expense" and not e.shared),
                ZERO,
            ),
            "accounts": accounts(user, db),
            "by_category": by_category,
            "members": [
                {
                    "id": m.id,
                    "name": m.name,
                    "income": sum(
                        (
                            e.amount
                            for e in selected
                            if e.kind == "income" and e.owner_id == m.id
                        ),
                        ZERO,
                    ),
                }
                for m in group_members
            ],
            "settlement": splits(selected, group_members),
            "overdue": sum(
                1
                for e in all_entries
                if e.kind == "expense"
                and not e.settled_date
                and e.due_date < date.today()
            ),
            "visibility": "Totais e saldos visíveis excluem lançamentos privados do outro integrante. Previsão usa somente lançamentos cadastrados no mês de vencimento.",
        },
        custom_encoder={Decimal: str},
    )
