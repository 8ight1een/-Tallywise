from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class TransactionCreate(BaseModel):
    account_id: int = Field(gt=0)
    category_id: int = Field(gt=0)
    money: Decimal = Field(gt=0, max_digits=9, decimal_places=2, allow_inf_nan=False)
    money_type: Literal["收入", "支出"]
    description: str | None = Field(default=None, max_length=250)
    transaction_date: date


class AccountCreate(BaseModel):
    name_accounts: Name


class CategoryCreate(BaseModel):
    name_categories: Name
    money_type: Literal["收入", "支出"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=32)
    nickname: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]


class UserLogin(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=32)


class OrmOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TransactionOut(OrmOut):
    id: int
    account_id: int
    category_id: int
    money: Decimal
    money_type: Literal["收入", "支出"]
    description: str | None
    transaction_date: date
    created_at: datetime


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    next_cursor: str | None
    has_more: bool


class AccountOut(OrmOut):
    id: int
    name_accounts: str
    created_at: datetime


class CategoryOut(OrmOut):
    id: int
    name_categories: str
    money_type: Literal["收入", "支出"]
    created_at: datetime


class UserOut(OrmOut):
    id: int
    email: EmailStr
    nickname: str | None


class LoginOut(BaseModel):
    message: str
    user: UserOut


class SummaryOut(BaseModel):
    money_in: Decimal
    money_out: Decimal
    money_sum: Decimal


class MessageOut(BaseModel):
    message: str
