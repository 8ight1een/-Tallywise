from pydantic import BaseModel, Field,EmailStr, StringConstraints
from typing import Literal, Annotated
from datetime import date
from decimal import Decimal

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


#请求模型
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
    password: str=Field(min_length=8, max_length=32)
    nickname: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]

class UserLogin(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=32)