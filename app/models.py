from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Family(Base):
    __tablename__ = "grupos_familiares"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    created_by: Mapped[UUID] = mapped_column(Uuid)


class User(Base):
    __tablename__ = "usuarios"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254))


class Membership(Base):
    __tablename__ = "integrantes_grupo"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    family_id: Mapped[UUID] = mapped_column(ForeignKey("grupos_familiares.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"))
    role: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean)


class Account(Base):
    __tablename__ = "contas_bancarias"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    family_id: Mapped[UUID] = mapped_column(ForeignKey("grupos_familiares.id"))
    name: Mapped[str] = mapped_column(String(120))
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)


class Category(Base):
    __tablename__ = "categorias"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    family_id: Mapped[UUID] = mapped_column(ForeignKey("grupos_familiares.id"))
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String)


class Entry(Base):
    __abstract__ = True
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    family_id: Mapped[UUID] = mapped_column(ForeignKey("grupos_familiares.id"))
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"))
    payer_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"))
    account_id: Mapped[UUID] = mapped_column(ForeignKey("contas_bancarias.id"))
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categorias.id"))
    description: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    kind: Mapped[str] = mapped_column(String)
    due_date: Mapped[date] = mapped_column(Date)
    settled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    shared: Mapped[bool] = mapped_column(Boolean, default=False)
    private: Mapped[bool] = mapped_column(Boolean, default=False)
    split_mode: Mapped[str] = mapped_column(String, default="equal")
    share_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=50)
    notes: Mapped[str] = mapped_column(String(2000), default="")
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)


class Income(Entry):
    __tablename__ = "receitas"


class Expense(Entry):
    __tablename__ = "despesas"


class Attachment(Base):
    __tablename__ = "anexos"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    family_id: Mapped[UUID] = mapped_column(ForeignKey("grupos_familiares.id"))
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"))
    expense_id: Mapped[UUID] = mapped_column(ForeignKey("despesas.id"))
    object_path: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String(200))
    content_type: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
