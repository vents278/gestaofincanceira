from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Family(Base):
    __tablename__ = "grupos_familiares"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))


class User(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("grupos_familiares.id"))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="member")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Account(Base):
    __tablename__ = "contas_bancarias"
    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("grupos_familiares.id"))
    name: Mapped[str] = mapped_column(String(120))
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)


class Category(Base):
    __tablename__ = "categorias"
    __table_args__ = (UniqueConstraint("family_id", "name", "kind"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("grupos_familiares.id"))
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(10))


class Entry(Base):
    __tablename__ = "lancamentos"
    __table_args__ = (
        CheckConstraint("amount > 0"),
        CheckConstraint("share_percent >= 0 AND share_percent <= 100"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("grupos_familiares.id"))
    owner_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    payer_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("contas_bancarias.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"))
    description: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    kind: Mapped[str] = mapped_column(String(10))
    due_date: Mapped[date] = mapped_column(Date)
    settled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    shared: Mapped[bool] = mapped_column(Boolean, default=False)
    private: Mapped[bool] = mapped_column(Boolean, default=False)
    split_mode: Mapped[str] = mapped_column(String(20), default="equal")
    share_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=50)
    notes: Mapped[str] = mapped_column(String(2000), default="")
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)


class Audit(Base):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("grupos_familiares.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    action: Mapped[str] = mapped_column(String(100))
    record_id: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
