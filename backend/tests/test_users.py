import pytest
from sqlalchemy import select

from auth import verify_password
from model import User
from schemas import UserCreate, UserLogin
from services.errors import AuthenticationError, BusinessConflictError
from services.users import login_user_service, register_user_service


def make_user(**overrides) -> UserCreate:
    data = {
        "email": "new@example.com",
        "password": "password123",
        "nickname": "新用户",
    }
    data.update(overrides)
    return UserCreate(**data)


async def test_注册成功返回用户(db):
    user = await register_user_service(db=db, data=make_user())
    assert user.id is not None
    assert user.email == "new@example.com"


async def test_重复邮箱注册被拒绝(db):
    await register_user_service(db=db, data=make_user())

    with pytest.raises(BusinessConflictError):
        await register_user_service(db=db, data=make_user(nickname="另一个人"))


async def test_邮箱会被归一化成小写(db):
    await register_user_service(db=db, data=make_user(email="Owner@Example.COM"))

    result = await db.execute(select(User).where(User.email == "owner@example.com"))
    assert result.scalar_one_or_none() is not None


async def test_密码以哈希形式存储而不是明文(db):
    await register_user_service(db=db, data=make_user(password="password123"))

    result = await db.execute(select(User).where(User.email == "new@example.com"))
    user = result.scalar_one()

    assert user.password_hash != "password123"
    assert verify_password("password123", user.password_hash) is True


async def test_邮箱不存在时登录失败(db):
    with pytest.raises(AuthenticationError):
        await login_user_service(
            db=db,
            data=UserLogin(email="nobody@example.com", password="password123"),
        )


async def test_密码错误时登录失败(db):
    await register_user_service(db=db, data=make_user())

    with pytest.raises(AuthenticationError):
        await login_user_service(
            db=db,
            data=UserLogin(email="new@example.com", password="wrong-password"),
        )


async def test_登录成功返回用户(db):
    created = await register_user_service(db=db, data=make_user())

    user = await login_user_service(
        db=db,
        data=UserLogin(email="new@example.com", password="password123"),
    )

    assert user.id == created.id
