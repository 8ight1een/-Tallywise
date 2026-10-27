import asyncio
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from model import Account, Category, IdempotencyKey, Transaction, User
from schemas import TransactionCreate
from services.errors import BusinessConflictError, ResourceNotFoundError
from services.ledger import (
    create_transaction_idempotent,
    get_idempotency_key,
    request_fingerprint,
)


@pytest.fixture
async def owner(db: AsyncSession) -> User:
    user = User(
        email="idempotency-owner@example.com",
        password_hash="not-a-real-hash",
        nickname="幂等所有者",
    )
    db.add(user)
    await db.commit()
    return user


@pytest.fixture
async def owner_account(db: AsyncSession, owner: User) -> Account:
    account = Account(user_id=owner.id, name_accounts="幂等现金")
    db.add(account)
    await db.commit()
    return account


@pytest.fixture
async def owner_category(db: AsyncSession, owner: User) -> Category:
    category = Category(user_id=owner.id, name_categories="幂等餐饮", money_type="支出")
    db.add(category)
    await db.commit()
    return category


def make_transaction(account_id, category_id, **overrides) -> TransactionCreate:
    data = {
        "account_id": account_id,
        "category_id": category_id,
        "money": Decimal("10.00"),
        "money_type": "支出",
        "transaction_date": date(2025, 1, 1),
    }
    data.update(overrides)
    return TransactionCreate(**data)


async def count_rows(db: AsyncSession, model) -> int:
    result = await db.execute(select(func.count()).select_from(model))
    return result.scalar_one()


def test_请求指纹稳定且随请求体变化():
    data = make_transaction(1, 2, description="咖啡")

    assert request_fingerprint(data) == request_fingerprint(
        make_transaction(1, 2, description="咖啡")
    )
    assert request_fingerprint(data) != request_fingerprint(
        make_transaction(1, 2, description="咖啡", money=Decimal("11.00"))
    )
    assert len(request_fingerprint(data)) == 64


def test_请求指纹与字段顺序无关():
    class Payload:
        def __init__(self, values):
            self.values = values

        def model_dump(self, mode):
            return self.values

    first = Payload({"balance": "10.00", "note": "咖啡"})
    second = Payload({"note": "咖啡", "balance": "10.00"})

    assert request_fingerprint(first) == request_fingerprint(second)


async def test_顺序重复请求返回同一条流水(db, owner, owner_account, owner_category):
    data = make_transaction(owner_account.id, owner_category.id)
    request_hash = request_fingerprint(data)

    first, created = await create_transaction_idempotent(
        db=db,
        user_id=owner.id,
        idem_key="sequential-key",
        request_hash=request_hash,
        data=data,
    )
    assert created is True
    await db.commit()

    second, replayed = await create_transaction_idempotent(
        db=db,
        user_id=owner.id,
        idem_key="sequential-key",
        request_hash=request_hash,
        data=data,
    )
    assert replayed is False
    assert second.id == first.id
    await db.commit()

    assert await count_rows(db, Transaction) == 1
    row = await get_idempotency_key(db, owner.id, "sequential-key")
    assert row is not None
    assert row.transaction_id == first.id


async def test_同一个键不同请求体被拒绝(db, owner, owner_account, owner_category):
    first = make_transaction(owner_account.id, owner_category.id)
    first_txn, created = await create_transaction_idempotent(
        db=db,
        user_id=owner.id,
        idem_key="different-body-key",
        request_hash=request_fingerprint(first),
        data=first,
    )
    assert created is True
    await db.commit()
    first_id = first_txn.id

    second = make_transaction(owner_account.id, owner_category.id, money=Decimal("20.00"))

    with pytest.raises(BusinessConflictError):
        await create_transaction_idempotent(
            db=db,
            user_id=owner.id,
            idem_key="different-body-key",
            request_hash=request_fingerprint(second),
            data=second,
        )

    await db.rollback()
    assert await count_rows(db, Transaction) == 1
    assert (await db.get(Transaction, first_id)).money == Decimal("10.00")


async def test_不同键相同请求体创建两条流水(db, owner, owner_account, owner_category):
    data = make_transaction(owner_account.id, owner_category.id)
    request_hash = request_fingerprint(data)

    first, first_created = await create_transaction_idempotent(
        db=db,
        user_id=owner.id,
        idem_key="first-key",
        request_hash=request_hash,
        data=data,
    )
    assert first_created is True
    await db.commit()

    second, second_created = await create_transaction_idempotent(
        db=db,
        user_id=owner.id,
        idem_key="second-key",
        request_hash=request_hash,
        data=data,
    )
    assert second_created is True
    await db.commit()

    assert first.id != second.id
    assert await count_rows(db, Transaction) == 2
    assert await count_rows(db, IdempotencyKey) == 2


async def test_事务失败时幂等键回滚且可以重试(db, owner, owner_account, owner_category):
    owner_id = owner.id
    account_id = owner_account.id
    category_id = owner_category.id
    failing = make_transaction(account_id, 999999)

    with pytest.raises(ResourceNotFoundError):
        await create_transaction_idempotent(
            db=db,
            user_id=owner_id,
            idem_key="retry-key",
            request_hash=request_fingerprint(failing),
            data=failing,
        )

    await db.rollback()
    assert await count_rows(db, IdempotencyKey) == 0
    assert await count_rows(db, Transaction) == 0

    retry = make_transaction(account_id, category_id)
    txn, created = await create_transaction_idempotent(
        db=db,
        user_id=owner_id,
        idem_key="retry-key",
        request_hash=request_fingerprint(retry),
        data=retry,
    )
    assert created is True
    await db.commit()

    assert await count_rows(db, Transaction) == 1
    row = await get_idempotency_key(db, owner_id, "retry-key")
    assert row is not None
    assert row.transaction_id == txn.id


async def test_两个会话并发提交同一个键只创建一条流水(db, owner, owner_account, owner_category):
    owner_id = owner.id
    data = make_transaction(owner_account.id, owner_category.id)
    request_hash = request_fingerprint(data)
    barrier = asyncio.Barrier(2)

    async def worker():
        async with AsyncSession(bind=db.bind, expire_on_commit=False) as session, session.begin():
            await barrier.wait()
            txn, created = await create_transaction_idempotent(
                db=session,
                user_id=owner_id,
                idem_key="race-key",
                request_hash=request_hash,
                data=data,
            )
            return txn.id, created

    results = await asyncio.gather(worker(), worker())
    await db.rollback()

    assert sorted(created for _txn_id, created in results) == [False, True]
    transaction_ids = {txn_id for txn_id, _created in results}
    assert len(transaction_ids) == 1

    assert await count_rows(db, Transaction) == 1
    assert await count_rows(db, IdempotencyKey) == 1
    row = await get_idempotency_key(db, owner_id, "race-key")
    assert row is not None
    assert row.transaction_id == transaction_ids.pop()
