from fastapi import APIRouter, Depends, HTTPException,status,Path,Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,func

from database import get_session
from model import Transaction, Account, Category, User
from schemas import TransactionCreate, AccountCreate, CategoryCreate
from auth import get_current_user
from services.ledger import (
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



router = APIRouter(prefix="/api", tags=["记账接口"])


@router.get("/health")
def health_check():
    return {"message": "后端连接成功"}



#查
@router.get("/transactions")
async def transactions(
        db: AsyncSession = Depends(get_session),
        current_users: User = Depends(get_current_user)
):
    result=await db.execute(select(Transaction).where(Transaction.user_id == current_users.id))
    return result.scalars().all()


@router.get("/accounts")
async def get_accounts(
        db: AsyncSession = Depends(get_session),
        current_users: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Account).where(Account.user_id == current_users.id)
    )
    return result.scalars().all()


@router.get("/categories")
async def get_categories(
    money_type: str,
    db: AsyncSession = Depends(get_session),
    current_users: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Category).where(
            Category.user_id == current_users.id,
            Category.money_type == money_type
        )
    )
    return result.scalars().all()




#增
@router.post("/transactions")
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


@router.post("/accounts")
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


@router.post("/categories")
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
@router.post("/transactions/{transaction_id}")
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



@router.post("/accounts/{account_id}")
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


@router.post("/categories/{category_id}")
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


@router.delete("/accounts/{account_id}")
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


@router.delete("/categories/{category_id}")
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
@router.get("/summary")
async def get_summary(
        year: int | None = Query(default=None, ge=1, le=9999),
        month: int | None = Query(default=None, ge=1, le=12),
        db: AsyncSession = Depends(get_session),
        current_users: User = Depends(get_current_user)
):
    if (year is None) != (month is None):
        raise HTTPException(
            status_code=422,
            detail="年份和月份必须一起提供",
        )

    if year is None:
        current_year = func.extract("year", func.now())
        current_month = func.extract("month", func.now())

    else:
        current_year = year
        current_month = month

    month_out = select(func.sum(Transaction.money)).where(
    Transaction.money_type == "支出",
    func.extract("year", Transaction.transaction_date) == current_year,
    func.extract("month",Transaction.transaction_date) == current_month,
    Transaction.user_id ==current_users.id
    )
    out_result = await db.execute(month_out)
    money_out = out_result.scalar_one_or_none() or 0

    month_in=select(func.sum(Transaction.money)).where(
    Transaction.money_type=="收入",
    func.extract("year",Transaction.transaction_date)==current_year,
    func.extract("month",Transaction.transaction_date)==current_month,
    Transaction.user_id == current_users.id
    )
    in_result = await db.execute(month_in)
    money_in=in_result.scalar_one_or_none() or 0


    return{
      "money_in":money_in,
      "money_out":money_out,
      "money_sum":money_in-money_out,
    }

@router.get("/transactions/{year}/{month}")
async def get_transactions_by_month(
    year: int=Path(...,ge=1,le=9999),
    month: int = Path(..., ge=1, le=12),
    db: AsyncSession = Depends(get_session),
    current_users: User = Depends(get_current_user),
):
    statement = (
        select(Transaction)
        .where(
            Transaction.user_id == current_users.id,
            func.extract("year", Transaction.transaction_date) == year,
            func.extract("month", Transaction.transaction_date) == month,
        )
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
    )

    result = await db.execute(statement)
    return result.scalars().all()
