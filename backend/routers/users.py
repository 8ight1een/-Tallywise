import os

from sqlalchemy.ext.asyncio import AsyncSession
from model import User
from auth import hash_password,verify_password,ACCESS_TOKEN_EXPIRE_MINUTES,create_access_token
from schemas import  UserCreate,UserLogin
from sqlalchemy import   select
from fastapi import Depends, HTTPException, APIRouter,Response
from starlette.concurrency import run_in_threadpool
from database import get_session,commit_session


router = APIRouter(prefix="/api", tags=["用户"])

@router.post("/auth/register")
async def register(
        data:UserCreate,
        db: AsyncSession = Depends(get_session),
):
    email = data.email.strip().lower()
    result=await db.execute(select(User).where(User.email==email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409,detail="该邮箱已注册")

    new_user = User(
        email=email,
        password_hash=await run_in_threadpool(hash_password,data.password),
        nickname=data.nickname,
    )

    db.add(new_user)
    await commit_session(db,"该邮箱已注册")

    return{
        "id": new_user.id,
        "email": new_user.email,
        "nickname": new_user.nickname,
    }


@router.post("/auth/login")
async def login(
        data:UserLogin,
        response: Response,
        db: AsyncSession = Depends(get_session),
):
    email = data.email.strip().lower()
    result=await db.execute(select(User).where(User.email==email))
    user = result.scalar_one_or_none()
    if user is None or not await run_in_threadpool(verify_password,data.password,user.pass_hash):
        raise HTTPException(status_code=401,detail="邮箱或密码错误")

    response.set_cookie(
        key="access_token",
        value=create_access_token(user.id),
        httponly=True,
        samesite="lax",
        secure=os.getenv("COOKIE_SECURE","false").lower() == "true",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES*60,
    )

@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")

    return {
        "message": "已退出登录"
    }