from sqlalchemy import URL
import os
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker,AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

DATABASE_URL =URL.create(
    drivername='mysql+aiomysql',
    username=os.getenv("DATABASE_USERNAME"),
    password=os.getenv("DATABASE_PASSWORD"),
    host=os.getenv("DATABASE_HOST"),
    database=os.getenv("DATABASE_NAME"),
    port=3306,
    query={"charset": "utf8"}
)

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal =async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_session():
    try:
        async with AsyncSessionLocal() as session:
            yield session
    except Exception:
        raise


async def commit_session(session: AsyncSession,detail:str):
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409,detail=detail) from None
