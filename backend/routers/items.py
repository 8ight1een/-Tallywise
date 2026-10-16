from fastapi import APIRouter, Depends, HTTPException,status,Path,Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from model import User
from schemas import (
    TransactionCreate,
    AccountCreate,
    CategoryCreate,
    TransactionOut,
    AccountOut,
    CategoryOut,
    SummaryOut,
    MessageOut,
)
from auth import get_current_user
from services.ledger import (
    get_transactions_service,
    get_accounts_service,
    get_categories_service,
    create_transaction_service,
    update_transaction_service,
    delete_transaction_service,
    update_category_service,
    create_category_service,
    delete_category_service,
    create_account_service,
    update_account_service,
    delete_account_service,
)
from services.reports import (
    get_transactions_by_month_service,
    get_summary_service,
)


router = APIRouter(prefix="/api", tags=["记账接口"])


@router.get("/health", response_model=MessageOut)
def health_check():
    return {"message": "后端连接成功"}



#查
@router.get("/transactions", response_model=list[TransactionOut])
async def transactions(
        db: AsyncSession = Depends(get_session),
        current_users: User = Depends(get_current_user)
):
    return await get_transactions_service(
        db=db,
        user_id=current_users.id,
    )


@router.get("/accounts", response_model=list[AccountOut])
async def get_accounts(
        db: AsyncSession = Depends(get_session),
        current_users: User = Depends(get_current_user)
):
    return await get_accounts_service(
        db=db,
        user_id=current_users.id,
    )


@router.get("/categories", response_model=list[CategoryOut])
async def get_categories(
    money_type: str,
    db: AsyncSession = Depends(get_session),
    current_users: User = Depends(get_current_user)
):
    return await get_categories_service(
        db=db,
        user_id=current_users.id,
        money_type=money_type,
    )




#增
@router.post("/transactions", response_model=TransactionOut)
async def add_transactions(
    data: TransactionCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await create_transaction_service(
        db=db,
        data=data,
        user_id=current_user.id,
    )


@router.post("/accounts", response_model=AccountOut)
async def add_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_session),
    current_users: User = Depends(get_current_user)
):
    return await create_account_service(
        db=db,
        data=data,
        user_id=current_users.id,
    )


@router.post("/categories", response_model=CategoryOut)
async def add_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_session),
    current_users: User = Depends(get_current_user)
):
    return await create_category_service(
        db=db,
        data=data,
        user_id=current_users.id
    )




#更
@router.post("/transactions/{transaction_id}", response_model=TransactionOut)
async def update_transaction(
    transaction_id: int,
    data: TransactionCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return await update_transaction_service(
        db=db,
        data=data,
        transaction_id=transaction_id,
        user_id=current_user.id,
    )



@router.post("/accounts/{account_id}", response_model=AccountOut)
async def update_account(
        account_id: int,
        data: AccountCreate,
        db: AsyncSession = Depends(get_session),
        current_users: User = Depends(get_current_user)
):
    return await update_account_service(
        db=db,
        data=data,
        account_id=account_id,
        user_id=current_users.id,
    )


@router.post("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
        category_id: int,
        data: CategoryCreate,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    return await update_category_service(
        db=db,
        data=data,
        category_id=category_id,
        user_id = current_user.id
    )




#删
@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await delete_transaction_service(
        db=db,
        transaction_id=transaction_id,
        user_id=current_user.id,
    )


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
    return {"message": "Category deleted"}


#月总结
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
