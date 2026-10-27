import hashlib
import json
from typing import Literal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from model import Account, Category, IdempotencyKey, Transaction
from schemas import AccountCreate, CategoryCreate, TransactionCreate
from services.db_errors import is_constraint_violation
from services.errors import (
    BusinessConflictError,
    MoneyTypeMismatchError,
    ResourceNotFoundError,
)


async def get_transactions_service(db: AsyncSession, user_id: int):
    result = await db.execute(select(Transaction).where(Transaction.user_id == user_id))
    return result.scalars().all()


async def get_accounts_service(db: AsyncSession, user_id: int):
    result = await db.execute(select(Account).where(Account.user_id == user_id))
    return result.scalars().all()


async def get_categories_service(
    db: AsyncSession,
    user_id: int,
    money_type: Literal["收入", "支出"],
):
    result = await db.execute(
        select(Category).where(
            Category.user_id == user_id,
            Category.money_type == money_type,
        )
    )
    return result.scalars().all()


async def get_owned(db, model, resource_id, user_id):
    result = await db.execute(
        select(model).where(
            model.id == resource_id,
            model.user_id == user_id,
        )
    )

    resource = result.scalar_one_or_none()

    if resource is None:
        raise ResourceNotFoundError("账户或分类不存在")

    return resource


async def lock_owned(db, model, resource_id, user_id):
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
    await get_owned(db, Account, data.account_id, user_id)

    category = await get_owned(db, Category, data.category_id, user_id)

    if category.money_type != data.money_type:
        raise MoneyTypeMismatchError("分类与流水的收支类型不一致")


def is_category_name_conflict(exc: IntegrityError) -> bool:
    return is_constraint_violation(exc, "23505", "categories_user_id_name_categories_key")


FK_IN_USE_SQLSTATES = ("23001", "23503")


def is_category_in_use(exc: IntegrityError) -> bool:
    return any(
        is_constraint_violation(exc, code, "transactions_category_id_fkey")
        for code in FK_IN_USE_SQLSTATES
    )


def is_account_in_use(exc: IntegrityError) -> bool:
    return any(
        is_constraint_violation(exc, code, "transactions_account_id_fkey")
        for code in FK_IN_USE_SQLSTATES
    )


async def create_transaction_service(
    db: AsyncSession,
    data: TransactionCreate,
    user_id: int,
) -> Transaction:
    await validate_references(db, data, user_id)

    transaction = Transaction(
        **data.model_dump(),
        user_id=user_id,
    )

    db.add(transaction)
    await db.flush()
    return transaction


async def update_transaction_service(
    db: AsyncSession, data: TransactionCreate, transaction_id: int, user_id: int
) -> Transaction:
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
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
    await db.flush()
    return transaction


async def delete_transaction_service(db: AsyncSession, transaction_id: int, user_id: int) -> None:
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
    )
    transaction = result.scalar_one_or_none()
    if transaction is None:
        raise ResourceNotFoundError("Transaction not found")
    await db.delete(transaction)
    await db.flush()


async def update_category_service(
    db: AsyncSession,
    data: CategoryCreate,
    category_id: int,
    user_id: int,
) -> Category:
    category = await lock_owned(db, Category, category_id, user_id)
    if category.money_type != data.money_type:
        existing = await db.execute(
            select(Transaction.id).where(Transaction.category_id == category_id).limit(1)
        )
        if existing.first() is not None:
            raise BusinessConflictError("分类已有流水，不能修改收支类型")
    category.name_categories = data.name_categories
    category.money_type = data.money_type
    try:
        await db.flush()
    except IntegrityError as exc:
        if is_category_name_conflict(exc):
            raise BusinessConflictError("该分类名称已存在") from exc
        raise
    return category


async def create_category_service(
    db: AsyncSession,
    data: CategoryCreate,
    user_id: int,
) -> Category:
    category = Category(
        user_id=user_id, name_categories=data.name_categories, money_type=data.money_type
    )

    db.add(category)
    try:
        await db.flush()
    except IntegrityError as exc:
        if is_category_name_conflict(exc):
            raise BusinessConflictError("该分类名称已存在") from exc
        raise
    return category


async def delete_category_service(
    db: AsyncSession,
    user_id: int,
    category_id: int,
) -> None:
    category = await lock_owned(db, Category, category_id, user_id)
    await db.delete(category)
    try:
        await db.flush()
    except IntegrityError as exc:
        if is_category_in_use(exc):
            raise BusinessConflictError("分类已有流水，不能删除") from exc
        raise


async def create_account_service(
    db: AsyncSession,
    data: AccountCreate,
    user_id: int,
) -> Account:
    account = Account(
        user_id=user_id,
        name_accounts=data.name_accounts,
    )
    db.add(account)
    await db.flush()
    return account


async def update_account_service(
    db: AsyncSession,
    data: AccountCreate,
    account_id: int,
    user_id: int,
) -> Account:
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
    await db.flush()
    return account


async def delete_account_service(
    db: AsyncSession,
    account_id: int,
    user_id: int,
) -> None:
    account = await lock_owned(db, Account, account_id, user_id)
    await db.delete(account)
    try:
        await db.flush()
    except IntegrityError as exc:
        if is_account_in_use(exc):
            raise BusinessConflictError("账户已有流水，不能删除") from exc
        raise


def request_fingerprint(data) -> str:
    canonical = json.dumps(
        data.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


async def claim_idempotency_key(db, user_id, idem_key, request_hash) -> bool:
    stmt = (
        insert(IdempotencyKey)
        .values(
            user_id=user_id,
            idem_key=idem_key,
            request_hash=request_hash,
        )
        .on_conflict_do_nothing(index_elements=["user_id", "idem_key"])
        .returning(IdempotencyKey.user_id)
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def get_idempotency_key(db, user_id, idem_key):
    result = await db.execute(
        select(IdempotencyKey).where(
            IdempotencyKey.user_id == user_id,
            IdempotencyKey.idem_key == idem_key,
        )
    )
    return result.scalar_one_or_none()


async def create_transaction_idempotent(
    db,
    user_id: int,
    idem_key: str,
    request_hash: str,
    data,
):
    claimed = await claim_idempotency_key(db, user_id, idem_key, request_hash)
    if not claimed:
        row = await get_idempotency_key(db, user_id, idem_key)
        if row is None:
            raise BusinessConflictError("幂等键状态异常，请重试")
        if row.request_hash != request_hash:
            raise BusinessConflictError("同一个幂等键不能用于不同请求")
        if row.transaction_id is None:
            raise BusinessConflictError("请求正在处理中，请稍后重试")
        txn = await db.get(Transaction, row.transaction_id)
        if txn is None:
            raise BusinessConflictError("原流水已不存在")
        return txn, False

    await validate_references(db, data, user_id)

    txn = Transaction(**data.model_dump(), user_id=user_id)
    db.add(txn)
    await db.flush()

    row = await get_idempotency_key(db, user_id, idem_key)
    if row is None:
        raise BusinessConflictError("幂等键状态异常，请重试")
    row.transaction_id = txn.id
    await db.flush()

    return txn, True
