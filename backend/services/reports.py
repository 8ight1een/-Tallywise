from calendar import monthrange
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from model import Account, Category, Transaction


def month_range(year: int, month: int) -> tuple[date, date | None]:
    start = date(year, month, 1)
    if year == 9999 and month == 12:
        return start, None
    end = start + relativedelta(months=1)
    return start, end


async def get_transactions_by_month_service(
    db: AsyncSession,
    user_id: int,
    year: int,
    month: int,
):
    start_date, end_date = month_range(year, month)
    statement = (
        select(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date < end_date
            if end_date is not None
            else Transaction.transaction_date <= date.max,
        )
        .order_by(
            Transaction.transaction_date.desc(),
            Transaction.id.desc(),
        )
    )

    result = await db.execute(statement)
    return result.scalars().all()


async def get_summary_service(
    db: AsyncSession,
    user_id: int,
    year: int | None = None,
    month: int | None = None,
):
    if (year is None) != (month is None):
        raise ValueError("年份和月份必须一起提供")

    if year is None or month is None:
        today = await db.scalar(select(func.current_date()))
        if today is None:
            raise RuntimeError("无法获取当前日期")
        year, month = today.year, today.month

    start_date, end_date = month_range(year, month)

    month_out = select(
        func.sum(Transaction.money),
        func.count(Transaction.id),
    ).where(
        Transaction.user_id == user_id,
        Transaction.money_type == "支出",
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date
        if end_date is not None
        else Transaction.transaction_date <= date.max,
    )
    out_result = await db.execute(month_out)
    money_out, expense_count = out_result.one()
    money_out = money_out or Decimal(0)

    month_in = select(
        func.sum(Transaction.money),
        func.count(Transaction.id),
    ).where(
        Transaction.user_id == user_id,
        Transaction.money_type == "收入",
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date
        if end_date is not None
        else Transaction.transaction_date <= date.max,
    )
    in_result = await db.execute(month_in)
    money_in, income_count = in_result.one()
    money_in = money_in or Decimal(0)

    return {
        "money_in": money_in,
        "money_out": money_out,
        "money_sum": money_in - money_out,
        "income_count": income_count,
        "expense_count": expense_count,
    }


async def get_daily_trend_service(
    db: AsyncSession,
    user_id: int,
    year: int,
    month: int,
):
    start_date, end_date = month_range(year, month)

    stmt = select(
        Transaction.transaction_date,
        Transaction.money_type,
        func.sum(Transaction.money).label("amount"),
    ).where(
        Transaction.user_id == user_id,
        Transaction.transaction_date >= start_date,
    )

    if end_date is None:
        stmt = stmt.where(Transaction.transaction_date <= date.max)
    else:
        stmt = stmt.where(Transaction.transaction_date < end_date)

    stmt = stmt.group_by(
        Transaction.transaction_date,
        Transaction.money_type,
    ).order_by(
        Transaction.transaction_date,
        Transaction.money_type,
    )

    result = await db.execute(stmt)
    rows = result.all()

    daily = {}
    days_in_month = monthrange(year, month)[1]
    for day_number in range(1, days_in_month + 1):
        current_date = date(year, month, day_number)
        daily[current_date] = {
            "transaction_date": current_date,
            "money_in": Decimal(0),
            "money_out": Decimal(0),
        }

    for row in rows:
        field = "money_in" if row.money_type == "收入" else "money_out"
        daily[row.transaction_date][field] = row.amount

    return list(daily.values())


async def get_category_expenses_service(
    db: AsyncSession,
    user_id: int,
    year: int,
    month: int,
):
    start_date, end_date = month_range(year, month)
    amount = func.sum(Transaction.money).label("amount")

    stmt = (
        select(
            Category.id.label("category_id"),
            Category.name_categories.label("category_name"),
            amount,
        )
        .select_from(Transaction)
        .join(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.money_type == "支出",
            Transaction.transaction_date >= start_date,
        )
    )

    if end_date is None:
        stmt = stmt.where(Transaction.transaction_date <= date.max)
    else:
        stmt = stmt.where(Transaction.transaction_date < end_date)

    stmt = stmt.group_by(
        Category.id,
        Category.name_categories,
    ).order_by(amount.desc(), Category.id)

    result = await db.execute(stmt)
    return [dict(row) for row in result.mappings().all()]


async def get_account_summary_service(
    db: AsyncSession,
    user_id: int,
    year: int,
    month: int,
):
    start_date, end_date = month_range(year, month)
    date_end = (
        Transaction.transaction_date < end_date
        if end_date is not None
        else Transaction.transaction_date <= date.max
    )

    stmt = (
        select(
            Account.id.label("account_id"),
            Account.name_accounts.label("account_name"),
            Transaction.money_type,
            func.sum(Transaction.money).label("amount"),
        )
        .select_from(Account)
        .outerjoin(
            Transaction,
            and_(
                Transaction.account_id == Account.id,
                Transaction.user_id == user_id,
                Transaction.transaction_date >= start_date,
                date_end,
            ),
        )
        .where(Account.user_id == user_id)
        .group_by(Account.id, Account.name_accounts, Transaction.money_type)
        .order_by(Account.id)
    )

    result = await db.execute(stmt)
    rows = result.all()
    accounts = {}

    for row in rows:
        if row.account_id not in accounts:
            accounts[row.account_id] = {
                "account_id": row.account_id,
                "account_name": row.account_name,
                "money_in": Decimal(0),
                "money_out": Decimal(0),
            }

        account = accounts[row.account_id]
        if row.money_type == "收入":
            account["money_in"] = row.amount
        elif row.money_type == "支出":
            account["money_out"] = row.amount

    for account in accounts.values():
        account["money_sum"] = account["money_in"] - account["money_out"]

    return list(accounts.values())
