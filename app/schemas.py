from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Register(Input):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    family_name: str = Field(default="Nosso grupo", min_length=2, max_length=120)
    invitation_code: str | None = Field(default=None, max_length=200)


class Login(Input):
    email: EmailStr
    password: str = Field(max_length=128)


class Recovery(Input):
    email: EmailStr


class PasswordUpdate(Input):
    password: str = Field(min_length=10, max_length=128)


class Callback(Input):
    access_token: str = Field(min_length=20, max_length=16000)
    refresh_token: str = Field(min_length=10, max_length=16000)


Money = Annotated[Decimal, Field(max_digits=15, decimal_places=2)]


class AccountIn(Input):
    name: str = Field(min_length=2, max_length=120)
    initial_balance: Money = Decimal("0")


class CategoryIn(Input):
    name: str = Field(min_length=2, max_length=120)
    kind: Literal["income", "expense"]


class EntryIn(Input):
    description: str = Field(min_length=2, max_length=200)
    amount: Money = Field(gt=0)
    kind: Literal["income", "expense"]
    due_date: date
    settled_date: date | None = None
    owner_id: UUID
    payer_id: UUID
    account_id: UUID
    category_id: UUID
    shared: bool = False
    private: bool = False
    split_mode: Literal["equal", "custom", "proportional"] = "equal"
    share_percent: Decimal = Field(
        default=Decimal("50"), ge=0, le=100, max_digits=5, decimal_places=2
    )
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def valid_visibility(self):
        if self.shared and (self.private or self.kind != "expense"):
            raise ValueError("Apenas despesas visíveis podem ser compartilhadas")
        if self.settled_date and self.settled_date > date.today():
            raise ValueError("Liquidação não pode estar no futuro")
        return self
