import base64
import json
from datetime import date

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from model import Transaction
from services.reports import month_range

Cursor = tuple[date, int]


def encode_cursor(transaction_date: date, transaction_id: int) -> str:
    raw = json.dumps(
        {"d": transaction_date.isoformat(), "id": transaction_id},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(token: str) -> Cursor:
    try:
        padded = token + "=" * (-len(token) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        if not isinstance(data, dict):
            raise ValueError("cursor payload must be an object")
        transaction_date = date.fromisoformat(data["d"])
        transaction_id = data["id"]
        if (
            isinstance(transaction_id, bool)
            or not isinstance(transaction_id, int)
            or not 1 <= transaction_id <= 2_147_483_647
        ):
            raise ValueError("transaction id must be a positive integer")
        return transaction_date, transaction_id
    except (ValueError, KeyError, TypeError, UnicodeError) as exc:
        raise ValueError("invalid cursor") from exc


async def list_transactions_page(
    db: AsyncSession,
    user_id: int,
    year: int,
    month: int,
    limit: int,
    cursor: Cursor | None = None,
) -> tuple[list[Transaction], str | None, bool]:
    start_date, end_date = month_range(year, month)

    stmt = select(Transaction).where(
        Transaction.user_id == user_id,
        Transaction.transaction_date >= start_date,
    )
    if end_date is None:
        stmt = stmt.where(Transaction.transaction_date <= date.max)
    else:
        stmt = stmt.where(Transaction.transaction_date < end_date)

    if cursor is not None:
        last_date, last_id = cursor
        stmt = stmt.where(
            tuple_(Transaction.transaction_date, Transaction.id) < (last_date, last_id)
        )

    stmt = stmt.order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).limit(
        limit + 1
    )

    rows = (await db.execute(stmt)).scalars().all()
    has_more = len(rows) > limit
    items = list(rows[:limit])
    next_cursor = (
        encode_cursor(items[-1].transaction_date, items[-1].id) if has_more and items else None
    )
    return items, next_cursor, has_more
