from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from model import Account, Category, Transaction, User
from schemas import CategoryCreate, TransactionCreate
from services.errors import (
    BusinessConflictError,
    MoneyTypeMismatchError,
    ResourceNotFoundError,
)
from services.ledger import (
    create_category_service,
    create_transaction_service,
    delete_account_service,
    delete_category_service,
    delete_transaction_service,
    update_transaction_service,
)


@pytest.fixture
async def owner(db: AsyncSession) -> User:
    user = User(
        email="owner@example.com",
        password_hash="not-a-real-hash",
        nickname="所有者",
    )
    db.add(user)
    await db.commit()
    return user


@pytest.fixture
async def stranger(db: AsyncSession) -> User:
    user = User(
        email="stranger@example.com",
        password_hash="not-a-real-hash",
        nickname="陌生人",
    )
    db.add(user)
    await db.commit()
    return user


@pytest.fixture
async def owner_account(db: AsyncSession, owner: User) -> Account:
    account = Account(user_id=owner.id, name_accounts="现金")
    db.add(account)
    await db.commit()
    return account


@pytest.fixture
async def owner_category(db: AsyncSession, owner: User) -> Category:
    category = Category(user_id=owner.id, name_categories="餐饮", money_type="支出")
    db.add(category)
    await db.commit()
    return category


@pytest.fixture
async def stranger_account(db: AsyncSession, stranger: User) -> Account:
    account = Account(user_id=stranger.id, name_accounts="陌生人的现金")
    db.add(account)
    await db.commit()
    return account


@pytest.fixture
async def stranger_category(db: AsyncSession, stranger: User) -> Category:
    category = Category(user_id=stranger.id, name_categories="陌生人的餐饮", money_type="支出")
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


async def test_可以创建自己的流水(db, owner, owner_account, owner_category):
    transaction = await create_transaction_service(
        db=db,
        data=make_transaction(owner_account.id, owner_category.id),
        user_id=owner.id,
    )

    assert transaction.id is not None
    assert transaction.user_id == owner.id
    assert await count_rows(db, Transaction) == 1


async def test_不能用别人的账户创建流水(db, owner, stranger, owner_account, owner_category):
    data = make_transaction(owner_account.id, owner_category.id)

    with pytest.raises(ResourceNotFoundError):
        await create_transaction_service(db=db, data=data, user_id=stranger.id)

    assert await count_rows(db, Transaction) == 0


async def test_不能更新别人的流水(
    db,
    owner,
    stranger,
    owner_account,
    owner_category,
    stranger_account,
    stranger_category,
):
    transaction = await create_transaction_service(
        db=db,
        data=make_transaction(owner_account.id, owner_category.id),
        user_id=owner.id,
    )
    tid = transaction.id

    with pytest.raises(ResourceNotFoundError):
        await update_transaction_service(
            db=db,
            data=make_transaction(
                stranger_account.id, stranger_category.id, money=Decimal("999.00")
            ),
            transaction_id=tid,
            user_id=stranger.id,
        )

    row = (await db.execute(select(Transaction).where(Transaction.id == tid))).scalar_one()
    assert row.money == Decimal("10.00")


async def test_不能删除别人的流水(db, owner, stranger, owner_account, owner_category):
    transaction = await create_transaction_service(
        db=db,
        data=make_transaction(owner_account.id, owner_category.id),
        user_id=owner.id,
    )

    with pytest.raises(ResourceNotFoundError):
        await delete_transaction_service(db=db, transaction_id=transaction.id, user_id=stranger.id)

    assert await count_rows(db, Transaction) == 1


async def test_分类收支类型与流水不一致时被拒绝(db, owner, owner_account, owner_category):
    data = make_transaction(owner_account.id, owner_category.id, money_type="收入")

    with pytest.raises(MoneyTypeMismatchError):
        await create_transaction_service(db=db, data=data, user_id=owner.id)


async def test_分类有流水时不能删除(db, owner, owner_account, owner_category):
    await create_transaction_service(
        db=db,
        data=make_transaction(owner_account.id, owner_category.id),
        user_id=owner.id,
    )

    with pytest.raises(BusinessConflictError):
        await delete_category_service(db=db, user_id=owner.id, category_id=owner_category.id)

    await db.rollback()
    assert await count_rows(db, Category) == 1


async def test_账户有流水时不能删除(db, owner, owner_account, owner_category):
    await create_transaction_service(
        db=db,
        data=make_transaction(owner_account.id, owner_category.id),
        user_id=owner.id,
    )

    with pytest.raises(BusinessConflictError):
        await delete_account_service(db=db, account_id=owner_account.id, user_id=owner.id)

    await db.rollback()
    assert await count_rows(db, Account) == 1


async def test_重复分类名被拒绝(db, owner, owner_category):
    with pytest.raises(BusinessConflictError):
        await create_category_service(
            db=db,
            data=CategoryCreate(name_categories="餐饮", money_type="支出"),
            user_id=owner.id,
        )

    await db.rollback()
    assert await count_rows(db, Category) == 1


async def test_不同用户可以取同名分类(db, owner, stranger):
    await create_category_service(
        db=db, data=CategoryCreate(name_categories="餐饮", money_type="支出"), user_id=owner.id
    )
    await create_category_service(
        db=db, data=CategoryCreate(name_categories="餐饮", money_type="支出"), user_id=stranger.id
    )

    assert await count_rows(db, Category) == 2


async def test_可以更新自己的流水(db, owner, owner_account, owner_category):
    transaction = await create_transaction_service(
        db=db,
        data=make_transaction(owner_account.id, owner_category.id),
        user_id=owner.id,
    )
    tid = transaction.id

    await update_transaction_service(
        db=db,
        data=make_transaction(
            owner_account.id, owner_category.id, money=Decimal("20.00"), description="改过了"
        ),
        transaction_id=tid,
        user_id=owner.id,
    )

    await db.commit()

    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncSession(bind=db.bind) as verification_db:
        row = (
            await verification_db.execute(select(Transaction).where(Transaction.id == tid))
        ).scalar_one()
        assert row.money == Decimal("20.00")
        assert row.description == "改过了"
