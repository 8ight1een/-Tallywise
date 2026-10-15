import os

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
)
from database import get_session
from model import User
from schemas import UserCreate, UserLogin
from services.users import register_user_service, login_user_service

router = APIRouter(prefix="/api", tags=["用户"])

@router.post("/auth/register")
async def register(
        data:UserCreate,
        db: AsyncSession = Depends(get_session),
):
    new_user = await register_user_service(
        db=db,
        data=data,
    )

    return {
        "id": new_user.id,
        "email": new_user.email,
        "nickname": new_user.nickname,
    }


@router.post("/auth/login")
async def login(
    data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    user = await login_user_service(
        db=db,
        data=data,
    )

    response.set_cookie(
        key="access_token",
        value=create_access_token(user.id),
        httponly=True,
        samesite="lax",
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return {
        "message": "登录成功",
        "user": {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
        },
    }

@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")

    return {
        "message": "已退出登录"
    }

@router.get("/auth/me")
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "nickname": current_user.nickname,
    }