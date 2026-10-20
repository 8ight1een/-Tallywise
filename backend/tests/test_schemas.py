from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from schemas import (
    AccountCreate,
    CategoryCreate,
    TransactionCreate,
    UserCreate,
    UserLogin,
)


def make_transaction(**overrides):
    data = {
        "account_id": 1,
        "category_id": 1,
        "money": Decimal("10.00"),
        "money_type": "支出",
        "transaction_date": date(2025, 1, 1),
    }
    data.update(overrides)
    return data


@pytest.fixture
def valid_account_data():
    return {"name_accounts": "现金"}


@pytest.fixture
def valid_category_data():
    return {"name_categories": "餐饮", "money_type": "支出"}


@pytest.fixture
def valid_user_data():
    return {
        "email": "user@example.com",
        "password": "password123",
        "nickname": "用户",
    }


def test_合法交易可以构造出来():
    created = TransactionCreate(**make_transaction())
    assert created.money == Decimal("10.00")
    assert created.money_type == "支出"
    assert created.description is None


@pytest.mark.parametrize(
    "money,reason",
    [
        (Decimal(0), "零"),
        (Decimal(-1), "负数"),
        (Decimal("-0.01"), "负的小数"),
    ],
)
def test_金额必须大于零(money, reason):
    with pytest.raises(ValidationError):
        TransactionCreate(**make_transaction(money=money))


@pytest.mark.parametrize(
    "money,reason",
    [
        (Decimal("0.001"), "三位小数"),
        (Decimal("1.234"), "多余精度"),
    ],
)
def test_金额最多两位小数(money, reason):
    with pytest.raises(ValidationError):
        TransactionCreate(**make_transaction(money=money))


def test_金额超过最大位数被拒绝():

    with pytest.raises(ValidationError):
        TransactionCreate(**make_transaction(money=Decimal("10000000.00")))


@pytest.mark.parametrize(
    "money,reason",
    [
        (Decimal("0.01"), "最小合法值"),
        (Decimal("10.00"), "普通值"),
        (Decimal("9999999.99"), "最大合法值"),
    ],
)
def test_合法金额被接受(money, reason):
    assert TransactionCreate(**make_transaction(money=money)).money == money


def test_收支类型只接受收入或支出():
    with pytest.raises(ValidationError):
        TransactionCreate(**make_transaction(money_type="转账"))


def test_收支类型收入也被接受():
    assert TransactionCreate(**make_transaction(money_type="收入")).money_type == "收入"


def test_账户id要合理():
    with pytest.raises(ValidationError):
        TransactionCreate(**make_transaction(account_id=0))


def test_分类id要合理():
    with pytest.raises(ValidationError):
        TransactionCreate(**make_transaction(category_id=0))


def test_描述超过250字被拒绝():
    with pytest.raises(ValidationError):
        TransactionCreate(**make_transaction(description="a" * 251))


def test_描述可以是空():
    assert TransactionCreate(**make_transaction(description=None)).description is None


def test_账户名不能为空(valid_account_data):
    with pytest.raises(ValidationError):
        AccountCreate(**{**valid_account_data, "name_accounts": ""})


def test_账户名不能只有空白(valid_account_data):
    with pytest.raises(ValidationError):
        AccountCreate(**{**valid_account_data, "name_accounts": "   "})


def test_账户名超过100字被拒绝(valid_account_data):
    with pytest.raises(ValidationError):
        AccountCreate(**{**valid_account_data, "name_accounts": "a" * 101})


def test_账户名两端空白会被去掉(valid_account_data):
    created = AccountCreate(**{**valid_account_data, "name_accounts": "  现金  "})
    assert created.name_accounts == "现金"


def test_分类名不能只有空白(valid_category_data):
    with pytest.raises(ValidationError):
        CategoryCreate(**{**valid_category_data, "name_categories": "   "})


def test_分类名超过100字被拒绝(valid_category_data):
    with pytest.raises(ValidationError):
        CategoryCreate(**{**valid_category_data, "name_categories": "a" * 101})


def test_分类的收支类型必须合法(valid_category_data):
    with pytest.raises(ValidationError):
        CategoryCreate(**{**valid_category_data, "money_type": "转账"})


@pytest.mark.parametrize(
    "password,reason",
    [
        ("1234567", "只有7位"),
        ("a" * 33, "超过32位"),
    ],
)
def test_密码长度必须在8到32之间(valid_user_data, password, reason):
    with pytest.raises(ValidationError):
        UserCreate(**{**valid_user_data, "password": password})


def test_密码8位被接受(valid_user_data):
    created = UserCreate(**{**valid_user_data, "password": "12345678"})
    assert created.password == "12345678"


def test_注册邮箱格式必须合法(valid_user_data):
    with pytest.raises(ValidationError):
        UserCreate(**{**valid_user_data, "email": "not-an-email"})


def test_昵称不能只有空白(valid_user_data):
    with pytest.raises(ValidationError):
        UserCreate(**{**valid_user_data, "nickname": "   "})


def test_登录邮箱不做格式校验_已知缺口():
    login = UserLogin(email="not-an-email", password="x")
    assert login.email == "not-an-email"
