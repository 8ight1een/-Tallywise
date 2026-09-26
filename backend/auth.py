import os
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, Cookie, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta,timezone

from database import get_session
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from model import User

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError('SECRET_KEY not set')

ALGORITHMS = ['HS256']
ACCESS_TOKEN_EXPIRE_MINUTES = 60

hasher_tool=PasswordHash.recommended()

def hash_password(password):
    return hasher_tool.hash(password)

def verify_password(plain_password:str, hashed_password:str) -> bool:
    try:
        return hasher_tool.verify(plain_password, hashed_password)
    except UnknownHashError:
        return False

def create_access_token(user_id:str) -> str:
    payload = {
        'sub': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHMS
    )

async def get_current_user(
        access_token:str | None =Cookie(default=None),
        db: AsyncSession = Depends(get_session)
) -> User:
    if access_token is None:
        raise HTTPException(status_code=401, detail='请先登录')

    try:
        payload = jwt.decode(
            access_token,
            SECRET_KEY,
            algorithms=['HS256'],
            options={"require":["exp","sub"]}
        )

        user_id = int(payload.get('sub'))

    except (InvalidTokenError,ValueError,TypeError):
        raise HTTPException(status_code=401,detail="登录已失效，请重新登录")

    user =await db.get(User,user_id)

    if user is None:
        raise HTTPException(status_code=401,detail="用户不存在")

    return user