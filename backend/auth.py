from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Cookie, Depends, HTTPException
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_session
from model import User

SECRET_KEY = settings.secret_key


ACCESS_TOKEN_EXPIRE_MINUTES = 60

hasher_tool = PasswordHash.recommended()


def hash_password(password):
    return hasher_tool.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return hasher_tool.verify(plain_password, hashed_password)
    except UnknownHashError:
        return False


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }

    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


async def get_current_user(
    access_token: str | None = Cookie(default=None), db: AsyncSession = Depends(get_session)
) -> User:
    if access_token is None:
        raise HTTPException(status_code=401, detail="请先登录")

    try:
        payload = jwt.decode(
            access_token, SECRET_KEY, algorithms=["HS256"], options={"require": ["exp", "sub"]}
        )

        sub = payload.get("sub")
        if sub is None:
            raise InvalidTokenError("token 缺少 sub")
        user_id = int(sub)

    except (InvalidTokenError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录") from exc

    user = await db.get(User, user_id)

    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user
