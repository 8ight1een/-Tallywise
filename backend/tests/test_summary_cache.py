from datetime import date
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import RedisError

from services import summary_cache


@pytest.fixture
def query(monkeypatch):
    query = AsyncMock(
        return_value={
            "money_in": "0",
            "money_out": "48.00",
            "money_sum": "-48.00",
            "income_count": 0,
            "expense_count": 1,
        }
    )
    monkeypatch.setattr(summary_cache, "get_summary_service", query)
    return query


async def test_repeat_read_uses_cached_summary(query):
    db, client = AsyncMock(), AsyncMock()
    client.get.return_value = None
    first = await summary_cache.get_cached_summary(db, client, 42, 2026, 11)
    payload = first.model_dump_json()
    key = "tallywise:summary:v1:42:2026-11"
    client.set.assert_awaited_once_with(key, payload, ex=60)
    client.get.return_value = payload
    assert await summary_cache.get_cached_summary(db, client, 42, 2026, 11) == first
    client.get.assert_awaited_with(key)
    query.assert_awaited_once_with(db, 42, 2026, 11)


@pytest.mark.parametrize("error", [RedisError(), TimeoutError()])
async def test_cache_failures_use_database_summary(query, error):
    db, client = AsyncMock(), AsyncMock()
    client.get.side_effect = error
    result = await summary_cache.get_cached_summary(db, client, 42, 2026, 11)
    client.set.assert_not_awaited()
    client.get.side_effect = None
    client.get.return_value = "broken json"
    client.set.side_effect = error
    assert await summary_cache.get_cached_summary(db, client, 42, 2026, 11) == result
    assert query.await_count == 2
    assert result.expense_count == 1
    client.delete.side_effect = error
    await summary_cache.invalidate_summary(client, 42, date(2026, 11, 20))


async def test_invalidate_only_affected_user_months():
    client = AsyncMock()
    await summary_cache.invalidate_summary(
        client, 42, date(2026, 11, 1), date(2026, 10, 1), date(2026, 10, 2)
    )
    client.delete.assert_awaited_once()
    assert sorted(client.delete.await_args.args) == [
        "tallywise:summary:v1:42:2026-10",
        "tallywise:summary:v1:42:2026-11",
    ]
