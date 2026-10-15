from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from model import Account, Category, Transaction
from schemas import AccountCreate, CategoryCreate, TransactionCreate
from services.errors import (
    BusinessConflictError,
    ResourceNotFoundError,
    MoneyTypeMismatchError,
)

async def owned_resource(db, model, resource_id, user_id):
    result = await db.execute(
        select(model)
        .where(
            model.id == resource_id,
            model.user_id == user_id,
        )
        .with_for_update()
    )

    resource = result.scalar_one_or_none()

    if resource is None:
        raise ResourceNotFoundError("账户或分类不存在")

    return resource

async def validate_references(db, data, user_id):
    await owned_resource(
        db, Account, data.account_id, user_id
    )

    category = await owned_resource(
        db, Category, data.category_id, user_id
    )

    if category.money_type != data.money_type:
        raise MoneyTypeMismatchError(
            "分类与流水的收支类型不一致"
        )


def is_constraint_violation(
    exc: IntegrityError,
    sqlstate: str,
    constraint_name: str,
) -> bool:
    db_error = exc.driver_exception
    return (
        getattr(db_error, "sqlstate", None) == sqlstate
        and getattr(db_error, "constraint_name", None) == constraint_name
    )


def is_category_name_conflict(exc: IntegrityError) -> bool:
    # 约束名称对应 database/schema_pg.sql 的 PostgreSQL 默认命名。
    return is_constraint_violation(
        exc, "23505", "categories_user_id_name_categories_key"
    )


def is_category_in_use(exc: IntegrityError) -> bool:
    return is_constraint_violation(exc, "23503", "transactions_category_id_fkey")


def is_account_in_use(exc: IntegrityError) -> bool:
    return is_constraint_violation(exc, "23503", "transactions_account_id_fkey")


async def create_transaction_service(
    db: AsyncSession,
    data: TransactionCreate,
    user_id: int,
) -> Transaction:
    try:
        await validate_references(db, data, user_id)

        transaction = Transaction(
            **data.model_dump(),
            user_id=user_id,
            created_at=datetime.now(),
        )

        db.add(transaction)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return transaction

async def update_transaction_service(
    db: AsyncSession,
    data: TransactionCreate,
    transaction_id:int,
    user_id:int
)-> Transaction:
    try:
        result = await db.execute(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id
            )
        )
        transaction = result.scalar_one_or_none()

        if transaction is None:
            raise ResourceNotFoundError("Transaction not found")


        await validate_references(db, data, user_id)
        transaction.account_id = data.account_id
        transaction.category_id = data.category_id
        transaction.money = data.money
        transaction.money_type = data.money_type
        transaction.description = data.description
        transaction.transaction_date = data.transaction_date
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return transaction

async def delete_transaction_service(
     db: AsyncSession,
     transaction_id: int,
     user_id:int
)-> None:
    try:
        result = await db.execute(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id
            )
        )
        transaction = result.scalar_one_or_none()
        if transaction is None:
            raise ResourceNotFoundError("Transaction not found")
        await db.delete(transaction)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

async def update_category_service(
    db: AsyncSession,
    data: CategoryCreate,
    category_id: int,
    user_id: int,
) -> Category:
    try:
        category = await owned_resource(db, Category, category_id, user_id)
        if category.money_type != data.money_type:
            existing = await db.execute(
                select(Transaction.id)
                .where(Transaction.category_id == category_id)
                .limit(1)
                .with_for_update()
            )
            if existing.first() is not None:
                raise BusinessConflictError("分类已有流水，不能修改收支类型")
        category.name_categories = data.name_categories
        category.money_type = data.money_type
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()

        if is_category_name_conflict(exc):
            raise BusinessConflictError(
                "该分类名称已存在"
            ) from exc

        raise

    except Exception:
        await db.rollback()
        raise

    return category

async def create_category_service(
    db: AsyncSession,
    data: CategoryCreate,
    user_id: int,
) -> Category:
    try:
        category = Category(
            user_id=user_id,
            name_categories=data.name_categories,
            money_type=data.money_type
        )

        db.add(category)
        await db.commit()
        await db.refresh(category)
    except IntegrityError as exc:
        await db.rollback()

        if is_category_name_conflict(exc):
            raise BusinessConflictError(
                "该分类名称已存在"
            ) from exc

        raise

    except Exception:
        await db.rollback()
        raise

    return category

async def delete_category_service(
    db: AsyncSession,
    user_id: int,
    category_id: int,
) -> None:
    try:
        category = await owned_resource(db, Category, category_id, user_id)
        await db.delete(category)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()

        if is_category_in_use(exc):
            raise BusinessConflictError(
                "分类已有流水，不能删除"
            ) from exc

        raise
    except Exception:
        await db.rollback()
        raise


async def create_account_service(
    db: AsyncSession,
    data: AccountCreate,
    user_id: int,
) -> Account:
    try:
        account = Account(
            user_id=user_id,
            name_accounts=data.name_accounts,
        )
        db.add(account)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await db.refresh(account)
    return account


async def update_account_service(
    db: AsyncSession,
    data: AccountCreate,
    account_id: int,
    user_id: int,
) -> Account:
    try:
        result = await db.execute(
            select(Account).where(
                Account.id == account_id,
                Account.user_id == user_id,
            )
        )
        account = result.scalar_one_or_none()
        if account is None:
            raise ResourceNotFoundError("Account not found")

        account.name_accounts = data.name_accounts
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return account


async def delete_account_service(
    db: AsyncSession,
    account_id: int,
    user_id: int,
) -> None:
    try:
        account = await owned_resource(db, Account, account_id, user_id)
        await db.delete(account)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if is_account_in_use(exc):
            raise BusinessConflictError("账户已有流水，不能删除") from exc
        raise
    except Exception:
        await db.rollback()
        raise
