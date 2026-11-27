import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from config import settings
from logging_config import setup_logging
from middleware import RequestIdMiddleware
from routers.ai import router as ai_router
from routers.items import router as items_router
from routers.users import router as users_router
from services.errors import (
    AuthenticationError,
    BusinessConflictError,
    MoneyTypeMismatchError,
    ResourceNotFoundError,
)

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = None
    if settings.redis_url:
        client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.3,
            socket_timeout=0.3,
        )
    app.state.redis = client
    try:
        yield
    finally:
        if client is not None:
            await client.aclose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(RequestIdMiddleware)


@app.exception_handler(ResourceNotFoundError)
async def handle_resource_not_found(
    _request: Request,
    exc: ResourceNotFoundError,
):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


@app.exception_handler(MoneyTypeMismatchError)
async def handle_money_type_mismatch(
    _request: Request,
    exc: MoneyTypeMismatchError,
):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )


@app.exception_handler(BusinessConflictError)
async def handle_business_conflict(
    _request: Request,
    exc: BusinessConflictError,
):
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc)},
    )


@app.exception_handler(AuthenticationError)
async def handle_authentication_error(
    _request: Request,
    exc: AuthenticationError,
):
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc)},
    )


logger = logging.getLogger("tallywise")


@app.exception_handler(Exception)
async def handle_unexpected(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "-")
    logger.error("未处理的异常", exc_info=exc, extra={"request_id": request_id})
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误", "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


app.include_router(users_router)
app.include_router(items_router)
app.include_router(ai_router)
