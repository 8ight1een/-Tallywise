from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from schemas import TransactionCreate


class DraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=500)
    reference_date: date

    @field_validator("text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("记账描述不能为空")
        return value


class Extraction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    single_transaction: bool
    account_id: int | None
    category_id: int | None
    money: str | None
    money_type: Literal["收入", "支出"] | None
    description: str | None
    transaction_date: str | None
    question: str | None


class DraftResult(BaseModel):
    status: Literal["ready", "needs_input"]
    fields: Extraction
    transaction: TransactionCreate | None
    issues: list[str]
    prompt_version: str
