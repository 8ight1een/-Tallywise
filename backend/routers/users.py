from sqlalchemy.ext.asyncio import AsyncSession
from model import User
from auth import hash_password
from database import get_session,commit_session
from schemas import  UserCreate
from sqlalchemy import   select
from fastapi import Depends, HTTPException, APIRouter
from starlette.concurrency import run_in_threadpool


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