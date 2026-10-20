import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from auth import hash_password, verify_password
from model import User
from schemas import UserCreate, UserLogin
from services.db_errors import is_constraint_violation
from services.errors import AuthenticationError, BusinessConflictError

logger = logging.getLogger("tallywise")


def mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:2]}***@{domain}" if len(name) > 2 else f"***@{domain}"


async def register_user_service(
    db: AsyncSession,
    data: UserCreate,
) -> User:
    email = data.email.strip().lower()

    result = await db.execute(select(User).where(User.email == email))

    if result.scalar_one_or_none() is not None:
        raise BusinessConflictError("该邮箱已注册")

    new_user = User(
        email=email,
        password_hash=await run_in_threadpool(hash_password, data.password),
        nickname=data.nickname,
    )

    db.add(new_user)
    try:
        await db.flush()
    except IntegrityError as exc:
        if is_constraint_violation(
            exc,
            "23505",
            "users_email_key",
        ):
            raise BusinessConflictError("该邮箱已注册") from exc
        raise
    return new_user


async def login_user_service(
    db: AsyncSession,
    data: UserLogin,
) -> User:
    email = data.email.strip().lower()

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("登录失败: 邮箱不存在 email=%s", mask_email(email))
        raise AuthenticationError("邮箱或密码错误")

    password_valid = await run_in_threadpool(
        verify_password,
        data.password,
        user.password_hash,
    )

    if not password_valid:
        raise AuthenticationError("邮箱或密码错误")

    return user
