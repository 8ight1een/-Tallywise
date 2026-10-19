import pytest
from sqlalchemy.exc import IntegrityError

from services.db_errors import is_constraint_violation
from services.ledger import is_account_in_use, is_category_in_use


class FakeDriverError(Exception):

    def __init__(self, sqlstate, constraint_name):
        super().__init__("fake driver error")
        self.sqlstate = sqlstate
        self.constraint_name = constraint_name


def make_integrity_error(sqlstate, constraint_name):
    return IntegrityError(
        "INSERT INTO users ...", {}, FakeDriverError(sqlstate, constraint_name)
    )


def test_sqlstate和约束名都匹配才返回真():
    exc = make_integrity_error("23505", "users_email_key")
    assert is_constraint_violation(exc, "23505", "users_email_key") is True


def test_sqlstate不匹配时返回假():
    exc = make_integrity_error("23503", "users_email_key")
    assert is_constraint_violation(exc, "23505", "users_email_key") is False


def test_约束名不匹配时返回假():
    exc = make_integrity_error("23505", "other_key")
    assert is_constraint_violation(exc, "23505", "users_email_key") is False


def test_底层异常没有这些属性时也不崩():
    exc = IntegrityError("INSERT INTO users ...", {}, Exception("plain error"))
    assert is_constraint_violation(exc, "23505", "users_email_key") is False


@pytest.mark.parametrize("check,constraint", [
    (is_account_in_use, "transactions_account_id_fkey"),
    (is_category_in_use, "transactions_category_id_fkey"),
])
@pytest.mark.parametrize("sqlstate", ["23001", "23503"])
def test_删除引用冲突同时识别两种状态且限定约束(check, constraint, sqlstate):
    assert check(make_integrity_error(sqlstate, constraint)) is True
    assert check(make_integrity_error(sqlstate, "other_constraint")) is False
    assert check(make_integrity_error("23505", constraint)) is False
