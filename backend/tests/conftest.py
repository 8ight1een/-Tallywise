import asyncio
import os
from collections.abc import AsyncGenerator
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
load_dotenv(BACKEND_DIR / ".env")

TEST_DB_NAME = os.getenv("TEST_DATABASE_NAME", "tallywise_test")
ORIGINAL_DB_NAME = os.getenv("DATABASE_NAME")


os.environ["DATABASE_NAME"] = TEST_DB_NAME

os.environ["SECRET_KEY"] = "tallywise-tests-only-secret-key-do-not-use-in-production"
os.environ["COOKIE_SECURE"] = "false"


if not TEST_DB_NAME.endswith("_test"):
    raise RuntimeError(
        f"拒绝运行测试：数据库名必须以 _test 结尾，当前是 {TEST_DB_NAME!r}。"
        "这是为了防止误删开发库/生产库的数据。"
    )


import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from database import DATABASE_URL, get_session
from main import app

SCHEMA_SQL_PATH = PROJECT_ROOT / "database" / "schema_pg.sql"

TABLES = ["transactions", "categories", "accounts", "users"]

engine = create_async_engine(DATABASE_URL, poolclass=NullPool, echo=False)

TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def _reset_schema() -> None:

    schema_sql = SCHEMA_SQL_PATH.read_text(encoding="utf-8")

    async with engine.begin() as conn:
        await conn.execute(text(f"DROP TABLE IF EXISTS {', '.join(TABLES)} CASCADE"))

        for statement in schema_sql.split(";"):
            if statement.strip():
                await conn.execute(text(statement))


async def _truncate_all() -> None:
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def prepare_database():
    if not os.getenv("TEST_DATABASE_NAME"):
        raise RuntimeError("数据库测试必须显式设置 TEST_DATABASE_NAME，指定可清空的专用测试库。")
    if TEST_DB_NAME == ORIGINAL_DB_NAME or DATABASE_URL.database != TEST_DB_NAME:
        raise RuntimeError("拒绝清库：测试库不能与原数据库相同，连接目标也必须匹配测试库名。")
    asyncio.run(_reset_schema())
    yield
    asyncio.run(engine.dispose())


@pytest.fixture
async def db(prepare_database) -> AsyncGenerator[AsyncSession]:

    await _truncate_all()
    async with TestSessionLocal() as session:
        yield session


async def _override_get_session():

    async with TestSessionLocal() as session, session.begin():
        yield session


@pytest.fixture(scope="session")
def _use_test_database():
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_session] = _override_get_session
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


@pytest.fixture
def client(prepare_database, _use_test_database):
    from fastapi.testclient import TestClient

    asyncio.run(_truncate_all())
    with TestClient(app) as c:
        yield c
