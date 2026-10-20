from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

DATABASE_URL = URL.create(
    drivername="postgresql+asyncpg",
    username=settings.database_username,
    password=settings.database_password,
    host=settings.database_host,
    database=settings.database_name,
    port=settings.database_port,
)

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.sql_echo,
    pool_size=10,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session():
    async with AsyncSessionLocal() as session, session.begin():
        yield session
