import asyncio
import logging
from datetime import date

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import SummaryOut
from services.reports import get_summary_service

log = logging.getLogger("tallywise")
TTL_SECONDS = 60


def summary_key(user_id: int, year: int, month: int) -> str:
    return f"tallywise:summary:v1:{user_id}:{year:04d}-{month:02d}"


async def get_cached_summary(
    db: AsyncSession, client: Redis | None, user_id: int, year: int, month: int
) -> SummaryOut:
    key = summary_key(user_id, year, month)
    if client is not None:
        try:
            async with asyncio.timeout(0.5):
                raw = await client.get(key)
            if raw is not None:
                result = SummaryOut.model_validate_json(raw)
                log.info("summary cache hit")
                return result
            log.info("summary cache miss")
        except RedisError, TimeoutError:
            log.warning("summary cache unavailable")
            client = None
        except ValidationError:
            log.warning("invalid cached summary")

    data = await get_summary_service(db, user_id, year, month)
    result = SummaryOut.model_validate(data)
    if client is not None:
        try:
            async with asyncio.timeout(0.5):
                await client.set(key, result.model_dump_json(), ex=TTL_SECONDS)
        except RedisError, TimeoutError:
            log.warning("summary cache write failed")
    return result


async def invalidate_summary(client: Redis | None, user_id: int, *dates: date) -> None:
    keys = {summary_key(user_id, day.year, day.month) for day in dates}
    if client is None or not keys:
        return
    try:
        async with asyncio.timeout(0.5):
            await client.delete(*keys)
    except RedisError, TimeoutError:
        log.warning("summary cache invalidation failed")
