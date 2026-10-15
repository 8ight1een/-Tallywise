from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from model import Transaction

async def get_transactions_by_month_service(
    db: AsyncSession,
    user_id: int,
    year: int,
    month: int,
):
    statement = (
        select(Transaction)
        .where(
            Transaction.user_id == user_id,
            func.extract("year", Transaction.transaction_date) == year,
            func.extract("month", Transaction.transaction_date) == month,
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
        current_year = func.extract("year", func.now())
        current_month = func.extract("month", func.now())
    else:
        current_year = year
        current_month = month
    month_out = select(func.sum(Transaction.money)).where(
        Transaction.user_id == user_id,
        Transaction.money_type == "支出",
        func.extract("year", Transaction.transaction_date) == current_year,
        func.extract("month", Transaction.transaction_date) == current_month,
    )
    out_result = await db.execute(month_out)
    money_out = out_result.scalar_one_or_none() or 0

    month_in = select(func.sum(Transaction.money)).where(
        Transaction.user_id == user_id,
        Transaction.money_type == "收入",
        func.extract("year", Transaction.transaction_date) == current_year,
        func.extract("month", Transaction.transaction_date) == current_month,
    )
    in_result = await db.execute(month_in)
    money_in = in_result.scalar_one_or_none() or 0

    return {
        "money_in": money_in,
        "money_out": money_out,
        "money_sum": money_in - money_out,
    }