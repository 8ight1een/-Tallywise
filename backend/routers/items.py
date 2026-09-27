from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException,status,Path,Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,func

from database import get_session, commit_session
from model import Transaction, Account, Category, User
from schemas import TransactionCreate, AccountCreate, CategoryCreate
from auth import get_current_user



router = APIRouter(prefix="/api", tags=["记账接口"])

async def owned_resource(db, model, resource_id, user_id):
    result = await db.execute(
        select(model).where(model.id == resource_id, model.user_id == user_id).with_for_update()
    )
    resource = result.scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=404, detail="账户或分类不存在")
    return resource


async def validate_references(db, data, user_id):
    await owned_resource(db, Account, data.account_id, user_id)
    category = await owned_resource(db, Category, data.category_id, user_id)
    if category.money_type != data.money_type:
        raise HTTPException(status_code=422, detail="分类与流水的收支类型不一致")





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
        current_users: User = Depends(get_current_user)
):
    await validate_references(db, data, current_users.id)
    transaction_obj = Transaction(
        **data.model_dump(),
        user_id=current_users.id,
        created_at=datetime.now()
    )

    db.add(transaction_obj)
    await db.commit()

    return transaction_obj


@router.post("/accounts")
async def add_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_session),
    current_users: User = Depends(get_current_user)
):
    account = Account(
        user_id=current_users.id,
        name_accounts=data.name_accounts
    )

    db.add(account)
    await db.commit()
    await db.refresh(account)

    return account


@router.post("/categories")
async def add_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_session),
    current_users: User = Depends(get_current_user)
):
    category = Category(
        user_id=current_users.id,
        name_categories=data.name_categories,
        money_type=data.money_type
    )

    db.add(category)
    await commit_session(db, "该分类名称已存在")
    await db.refresh(category)

    return category




#更
@router.post("/transactions/{transaction_id}")
async def update_transaction(
    transaction_id: int,
    data: TransactionCreate,
    db: AsyncSession = Depends(get_session),
    current_users: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id ==current_users.id
        )
    )
    transaction = result.scalar_one_or_none()

    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    await validate_references(db, data, current_users.id)
    transaction.account_id = data.account_id
    transaction.category_id = data.category_id
    transaction.money = data.money
    transaction.money_type = data.money_type
    transaction.description = data.description
    transaction.transaction_date = data.transaction_date
    await db.commit()
    return transaction


@router.post("/accounts/{account_id}")
async def update_account(
        account_id: int,
        data: AccountCreate,
        db: AsyncSession = Depends(get_session),
        current_users: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.user_id == current_users.id
        )
    )

    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    account.name_accounts = data.name_accounts
    await db.commit()
    return account


@router.post("/categories/{category_id}")
async def update_category(
        category_id: int,
        data: CategoryCreate,
        db: AsyncSession = Depends(get_session),
        current_users: User = Depends(get_current_user)
):
    category = await owned_resource(db, Category, category_id, current_users.id)
    if category.money_type != data.money_type:
        existing = await db.execute(
            select(Transaction.id)
            .where(Transaction.category_id == category_id)
            .limit(1)
            .with_for_update()
        )
        if existing.first() is not None:
            raise HTTPException(status_code=409, detail="分类已有流水，不能修改收支类型")
    category.name_categories = data.name_categories
    category.money_type = data.money_type
    await commit_session(db, "该分类名称已存在")
    return category



#删
@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id ==current_user.id
        )
    )
    transaction = result.scalar_one_or_none()

    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    await db.delete(transaction)
    await db.commit()


@router.delete("/accounts/{account_id}")
async def delete_account(
        account_id: int,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_user),
):
    account = await owned_resource(db, Account, account_id, current_user.id)
    await db.delete(account)
    await commit_session(db, "账户已有流水，不能删除")
    return {"message": "Account deleted"}


@router.delete("/categories/{category_id}")
async def delete_category(
        category_id: int,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_user),
):
    category = await owned_resource(db, Category, category_id, current_user.id)
    await db.delete(category)
    await commit_session(db, "分类已有流水，不能删除")
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
