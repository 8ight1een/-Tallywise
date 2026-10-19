from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from model import Account, Category, Transaction, User
from services import reports
from services.reports import (
    get_summary_service,
    get_transactions_by_month_service,
    month_range,
)


@pytest.mark.parametrize("year,month,expected", [
    (2025, 1,  (date(2025, 1, 1),  date(2025, 2, 1))),
    (2025, 2,  (date(2025, 2, 1),  date(2025, 3, 1))),
    (2024, 2,  (date(2024, 2, 1),  date(2024, 3, 1))),
    (2025, 3,  (date(2025, 3, 1),  date(2025, 4, 1))),
    (2025, 11, (date(2025, 11, 1), date(2025, 12, 1))),
    (2025, 12, (date(2025, 12, 1), date(2026, 1, 1))),
], ids=["1月", "平年2月", "闰年2月", "3月", "11月", "12月跨年"])
def test_月份区间是左闭右开(year, month, expected):
    assert month_range(year, month) == expected


def test_相邻月份首尾相接():
    for month in range(1, 12):
        _, end = month_range(2025, month)
        next_start, _ = month_range(2025, month + 1)
        assert end == next_start, f"{month} 月和 {month + 1} 月之间有缝"

    _, end = month_range(2025, 12)
    next_start, _ = month_range(2026, 1)
    assert end == next_start


@pytest.fixture
async def owner(db: AsyncSession) -> User:
    user = User(
        email="report@example.com",
        password_hash="not-a-real-hash",
        nickname="报表用户",
    )
    db.add(user)
    await db.commit()
    return user


@pytest.fixture
async def account(db: AsyncSession, owner: User) -> Account:
    row = Account(user_id=owner.id, name_accounts="现金")
    db.add(row)
    await db.commit()
    return row


@pytest.fixture
async def category(db: AsyncSession, owner: User) -> Category:
    row = Category(user_id=owner.id, name_categories="餐饮", money_type="支出")
    db.add(row)
    await db.commit()
    return row


async def add_transaction(
    db: AsyncSession,
    owner: User,
    account: Account,
    category: Category,
    *,
    day: date,
    money: str,
    money_type: str = "支出",
) -> Transaction:
    row = Transaction(
        user_id=owner.id,
        account_id=account.id,
        category_id=category.id,
        money=Decimal(money),
        money_type=money_type,
        transaction_date=day,
    )
    db.add(row)
    await db.commit()
    return row


async def test_汇总只统计指定月份(db, owner, account, category):
    await add_transaction(db, owner, account, category, day=date(2025, 3, 1), money="10.00")
    await add_transaction(db, owner, account, category, day=date(2025, 3, 31), money="20.00")
    await add_transaction(db, owner, account, category, day=date(2025, 2, 28), money="999.00")
    await add_transaction(db, owner, account, category, day=date(2025, 4, 1), money="999.00")

    result = await get_summary_service(db=db, user_id=owner.id, year=2025, month=3)

    assert result["money_out"] == Decimal("30.00")


async def test_收入和支出分开统计(db, owner, account, category):
    income_category = Category(user_id=owner.id, name_categories="工资", money_type="收入")
    db.add(income_category)
    await db.commit()
    await add_transaction(db, owner, account, income_category,
                          day=date(2025, 3, 1), money="100.00", money_type="收入")
    await add_transaction(db, owner, account, category,
                          day=date(2025, 3, 2), money="30.00", money_type="支出")

    result = await get_summary_service(db=db, user_id=owner.id, year=2025, month=3)

    assert result["money_in"] == Decimal("100.00")
    assert result["money_out"] == Decimal("30.00")
    assert result["money_sum"] == Decimal("70.00")


async def test_十二月和次年一月不会互相串(db, owner, account, category):
    await add_transaction(db, owner, account, category, day=date(2025, 12, 31), money="10.00")
    await add_transaction(db, owner, account, category, day=date(2026, 1, 1), money="20.00")

    december = await get_summary_service(db=db, user_id=owner.id, year=2025, month=12)
    january = await get_summary_service(db=db, user_id=owner.id, year=2026, month=1)

    assert december["money_out"] == Decimal("10.00")
    assert january["money_out"] == Decimal("20.00")


async def test_不会统计到别人的流水(db, owner, account, category):
    await add_transaction(db, owner, account, category, day=date(2025, 3, 1), money="10.00")

    stranger = User(email="other-report@example.com", password_hash="x", nickname="别人")
    db.add(stranger)
    await db.commit()

    stranger_account = Account(user_id=stranger.id, name_accounts="别人的现金")
    stranger_category = Category(
        user_id=stranger.id, name_categories="别人的餐饮", money_type="支出"
    )
    db.add_all([stranger_account, stranger_category])
    await db.commit()

    await add_transaction(db, stranger, stranger_account, stranger_category,
                          day=date(2025, 3, 1), money="999.00")

    result = await get_summary_service(db=db, user_id=owner.id, year=2025, month=3)

    assert result["money_out"] == Decimal("10.00")

    rows = await get_transactions_by_month_service(db=db, user_id=owner.id, year=2025, month=3)
    assert len(rows) == 1
    assert rows[0].user_id == owner.id


async def test_没有流水时汇总为零(db, owner):
    result = await get_summary_service(db=db, user_id=owner.id, year=2025, month=3)

    assert result["money_in"] == 0
    assert result["money_out"] == 0


async def test_不传年月时使用数据库月份(db, owner, account, category, monkeypatch):
    today = await db.scalar(select(func.current_date()))

    class DifferentLocalDate(date):
        @classmethod
        def today(cls):
            return date(2000 if today.year != 2000 else 2001, 1, 1)

    monkeypatch.setattr(reports, "date", DifferentLocalDate)
    await add_transaction(db, owner, account, category,
                          day=today.replace(day=1), money="10.00")
    await add_transaction(db, owner, account, category,
                          day=DifferentLocalDate.today(), money="999.00")

    result = await get_summary_service(db=db, user_id=owner.id)

    assert result["money_out"] == Decimal("10.00")


@pytest.mark.parametrize("kwargs", [{"year": 2025}, {"month": 3}],
                         ids=["只给year", "只给month"])
async def test_年月必须成对提供(db, owner, kwargs):
    with pytest.raises(ValueError):
        await get_summary_service(db=db, user_id=owner.id, **kwargs)


async def test_月度流水只返回该月记录(db, owner, account, category):
    march = await add_transaction(db, owner, account, category,
                                  day=date(2025, 3, 15), money="10.00")
    await add_transaction(db, owner, account, category, day=date(2025, 4, 1), money="20.00")
    await add_transaction(db, owner, account, category, day=date(2025, 2, 28), money="30.00")

    rows = await get_transactions_by_month_service(
        db=db, user_id=owner.id, year=2025, month=3
    )

    assert [row.id for row in rows] == [march.id]


async def test_月度流水包含月末最后一天(db, owner, account, category):
    await add_transaction(db, owner, account, category, day=date(2025, 3, 31), money="10.00")

    rows = await get_transactions_by_month_service(
        db=db, user_id=owner.id, year=2025, month=3
    )

    assert len(rows) == 1


async def test_月度流水按日期倒序(db, owner, account, category):
    await add_transaction(db, owner, account, category, day=date(2025, 3, 1), money="10.00")
    await add_transaction(db, owner, account, category, day=date(2025, 3, 20), money="20.00")
    await add_transaction(db, owner, account, category, day=date(2025, 3, 10), money="30.00")

    rows = await get_transactions_by_month_service(
        db=db, user_id=owner.id, year=2025, month=3
    )

    assert [row.transaction_date for row in rows] == [
        date(2025, 3, 20),
        date(2025, 3, 10),
        date(2025, 3, 1),
    ]


async def test_同一天按编号倒序(db, owner, account, category):
    first = await add_transaction(db, owner, account, category, day=date(2025, 3, 1), money="10.00")
    second = await add_transaction(db, owner, account, category, day=date(2025, 3, 1), money="20.00")
    rows = await get_transactions_by_month_service(db=db, user_id=owner.id, year=2025, month=3)
    assert [row.id for row in rows] == [second.id, first.id]


async def test_闰年二月包含29日且排除三月(db, owner, account, category):
    leap = await add_transaction(db, owner, account, category, day=date(2024, 2, 29), money="10.00")
    await add_transaction(db, owner, account, category, day=date(2024, 3, 1), money="999.00")
    rows = await get_transactions_by_month_service(db=db, user_id=owner.id, year=2024, month=2)
    result = await get_summary_service(db=db, user_id=owner.id, year=2024, month=2)
    assert [row.id for row in rows] == [leap.id]
    assert result["money_out"] == Decimal("10.00")


def test_最大年月不计算溢出的次年日期():
    assert month_range(9999, 12) == (date(9999, 12, 1), None)


async def test_最大年月保留最后一天(db, owner, account, category):
    last = await add_transaction(db, owner, account, category, day=date.max, money="10.00")
    await add_transaction(db, owner, account, category, day=date(9999, 11, 30), money="999.00")
    rows = await get_transactions_by_month_service(db=db, user_id=owner.id, year=9999, month=12)
    result = await get_summary_service(db=db, user_id=owner.id, year=9999, month=12)
    assert [row.id for row in rows] == [last.id]
    assert result["money_out"] == Decimal("10.00")
