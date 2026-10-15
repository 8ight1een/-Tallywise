from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

from fastapi import FastAPI
from routers.users import router as users_router
from routers.items import router as items_router
from fastapi import Request
from fastapi.responses import JSONResponse

from services.errors import (
    ResourceNotFoundError,
    MoneyTypeMismatchError,
    BusinessConflictError,
    AuthenticationError,
)

app = FastAPI()

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

app.include_router(users_router)
app.include_router(items_router)

