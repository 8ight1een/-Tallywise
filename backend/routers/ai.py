from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_config import ai_settings
from ai_drafts import AIError, generate_draft
from ai_schemas import BatchDraftRequest, BatchDraftResult, DraftRequest, DraftResult
from auth import get_current_user
from database import get_session
from model import Account, Category, User

router = APIRouter(prefix="/api/ai", tags=["AI 记账草稿"])


@router.post("/transaction-draft", response_model=DraftResult)
async def transaction_draft(
    data: DraftRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await _draft_response(data, db, current_user)


@router.post("/transaction-drafts", response_model=BatchDraftResult)
async def transaction_drafts(
    data: BatchDraftRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await _draft_response(data, db, current_user)


async def _draft_response(data: DraftRequest, db: AsyncSession, current_user: User):
    account_rows = (
        (
            await db.execute(
                select(Account)
                .where(Account.user_id == current_user.id)
                .order_by(Account.id)
                .limit(51)
            )
        )
        .scalars()
        .all()
    )
    category_rows = (
        (
            await db.execute(
                select(Category)
                .where(Category.user_id == current_user.id)
                .order_by(Category.id)
                .limit(101)
            )
        )
        .scalars()
        .all()
    )
    accounts = [{"id": row.id, "name": row.name_accounts} for row in account_rows]
    categories = [
        {"id": row.id, "name": row.name_categories, "money_type": row.money_type}
        for row in category_rows
    ]
    user_id = current_user.id
    await db.rollback()
    try:
        return await generate_draft(data, accounts, categories, ai_settings, user_id)
    except AIError as exc:
        raise HTTPException(
            status_code=exc.status,
            detail={"code": exc.code, "message": str(exc), "fallback": "manual_entry"},
        ) from exc
