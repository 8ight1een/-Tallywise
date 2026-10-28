from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_session
from model import User
from schemas import (
    AccountCreate,
    AccountOut,
    CategoryCreate,
    CategoryOut,
    MessageOut,
    SummaryOut,
    TransactionCreate,
    TransactionOut,
    TransactionPage,
)
from services.ledger import (
    create_account_service,
    create_category_service,
    create_transaction_idempotent,
    delete_account_service,
    delete_category_service,
    delete_transaction_service,
    get_accounts_service,
    get_categories_service,
    get_transactions_service,
    request_fingerprint,
    update_account_service,
    update_category_service,
    update_transaction_service,
)
from services.pagination import decode_cursor, list_transactions_page
from services.reports import (
    get_summary_service,
    get_transactions_by_month_service,
)

router = APIRouter(prefix="/api", tags=["记账接口"])


@router.get("/health", response_model=MessageOut)
async def health_check(db: AsyncSession = Depends(get_session)):
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="数据库不可用") from exc
    return {"message": "后端连接成功"}


@router.get("/transactions", response_model=list[TransactionOut])
async def transactions(
    db: AsyncSession = Depends(get_session), current_users: User = Depends(get_current_user)
):
    return await get_transactions_service(
        db=db,
        user_id=current_users.id,
    )


@router.get("/accounts", response_model=list[AccountOut])
async def get_accounts(
    db: AsyncSession = Depends(get_session), current_users: User = Depends(get_current_user)
):
    return await get_accounts_service(
        db=db,
        user_id=current_users.id,
    )


@router.get("/categories", response_model=list[CategoryOut])
async def get_categories(
    money_type: Literal["收入", "支出"],
    db: AsyncSession = Depends(get_session),
    current_users: User = Depends(get_current_user),
):
    return await get_categories_service(
        db=db,
        user_id=current_users.id,
        money_type=money_type,
    )


@router.post("/transactions", response_model=TransactionOut)
async def add_transactions(
    data: TransactionCreate,
    response: Response,
    idempotency_key: str = Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=200,
    ),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    request_hash = request_fingerprint(data)
    txn, created = await create_transaction_idempotent(
        db=db,
        user_id=current_user.id,
        idem_key=idempotency_key,
        request_hash=request_hash,
        data=data,
    )

    await db.commit()

    if created:
        response.status_code = 201
    else:
        response.headers["Idempotent-Replayed"] = "true"

    return txn


@router.post("/accounts", response_model=AccountOut)
async def add_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    account = await create_account_service(
        db=db,
        data=data,
        user_id=current_user.id,
    )

    await db.commit()

    return account


@router.post("/categories", response_model=CategoryOut)
async def add_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    category = await create_category_service(
        db=db,
        data=data,
        user_id=current_user.id,
    )

    await db.commit()

    return category


@router.put("/transactions/{transaction_id}", response_model=TransactionOut)
async def update_transaction(
    transaction_id: int,
    data: TransactionCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    transaction = await update_transaction_service(
        db=db,
        data=data,
        transaction_id=transaction_id,
        user_id=current_user.id,
    )

    await db.commit()

    return transaction


@router.put("/accounts/{account_id}", response_model=AccountOut)
async def update_account(
    account_id: int,
    data: AccountCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    account = await update_account_service(
        db=db,
        data=data,
        account_id=account_id,
        user_id=current_user.id,
    )

    await db.commit()

    return account


@router.put("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    data: CategoryCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    category = await update_category_service(
        db=db,
        data=data,
        category_id=category_id,
        user_id=current_user.id,
    )

    await db.commit()

    return category


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await delete_transaction_service(
        db=db,
        transaction_id=transaction_id,
        user_id=current_user.id,
    )

    await db.commit()


@router.delete("/accounts/{account_id}", response_model=MessageOut)
async def delete_account(
    account_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await delete_account_service(
        db=db,
        account_id=account_id,
        user_id=current_user.id,
    )

    await db.commit()

    return {"message": "Account deleted"}


@router.delete("/categories/{category_id}", response_model=MessageOut)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await delete_category_service(
        db=db,
        user_id=current_user.id,
        category_id=category_id,
    )

    await db.commit()

    return {"message": "Category deleted"}


@router.get("/summary", response_model=SummaryOut)
async def get_summary(
    year: int | None = Query(default=None, ge=1, le=9999),
    month: int | None = Query(default=None, ge=1, le=12),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if (year is None) != (month is None):
        raise HTTPException(
            status_code=422,
            detail="年份和月份必须一起提供",
        )

    return await get_summary_service(
        db=db,
        user_id=current_user.id,
        year=year,
        month=month,
    )


@router.get("/transactions/page", response_model=TransactionPage)
async def transactions_page(
    year: int = Query(..., ge=1, le=9999),
    month: int = Query(..., ge=1, le=12),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="分页游标无效") from exc
    else:
        decoded = None

    items, next_cursor, has_more = await list_transactions_page(
        db=db,
        user_id=current_user.id,
        year=year,
        month=month,
        limit=limit,
        cursor=decoded,
    )
    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }


@router.get("/transactions/{year}/{month}", response_model=list[TransactionOut])
async def get_transactions_by_month(
    year: int = Path(..., ge=1, le=9999),
    month: int = Path(..., ge=1, le=12),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await get_transactions_by_month_service(
        db=db,
        user_id=current_user.id,
        year=year,
        month=month,
    )
