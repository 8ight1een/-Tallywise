from sqlalchemy import URL
import os
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker,AsyncSession

DATABASE_URL =URL.create(
    drivername='postgresql+asyncpg',
    username=os.getenv("DATABASE_USERNAME"),
    password=os.getenv("DATABASE_PASSWORD"),
    host=os.getenv("DATABASE_HOST"),
    database=os.getenv("DATABASE_NAME"),
    port=5432,
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
