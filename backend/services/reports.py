from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from model import Transaction


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
            if end_date is not None else Transaction.transaction_date <= date.max,
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

    if year is None:
        today = await db.scalar(select(func.current_date()))
        year, month = today.year, today.month

    start_date, end_date = month_range(year, month)

    month_out = select(func.sum(Transaction.money)).where(
        Transaction.user_id == user_id,
        Transaction.money_type == "支出",
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date
        if end_date is not None else Transaction.transaction_date <= date.max,
    )
    out_result = await db.execute(month_out)
    money_out = out_result.scalar_one_or_none() or 0

    month_in = select(func.sum(Transaction.money)).where(
        Transaction.user_id == user_id,
        Transaction.money_type == "收入",
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date
        if end_date is not None else Transaction.transaction_date <= date.max,
    )
    in_result = await db.execute(month_in)
    money_in = in_result.scalar_one_or_none() or 0

    return {
        "money_in": money_in,
        "money_out": money_out,
        "money_sum": money_in - money_out,
    }
