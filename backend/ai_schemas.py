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


MAX_DRAFTS = 10


class BatchDraftRequest(DraftRequest):
    text: str = Field(min_length=1, max_length=1500)


class DraftFields(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    account_id: int | None
    category_id: int | None
    money: str | None
    money_type: Literal["收入", "支出"] | None
    description: str | None
    transaction_date: str | None
    question: str | None


class Extraction(DraftFields):
    single_transaction: bool


class BatchExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    drafts: list[DraftFields]
    warnings: list[str]
    too_many: bool


class ReviewedDraft(BaseModel):
    status: Literal["ready", "needs_input"]
    fields: DraftFields
    transaction: TransactionCreate | None
    issues: list[str]


class DraftResult(ReviewedDraft):
    fields: Extraction
    prompt_version: str


class BatchDraftResult(BaseModel):
    drafts: list[ReviewedDraft]
    warnings: list[str]
    prompt_version: str
