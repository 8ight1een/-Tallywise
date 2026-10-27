import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("password", ["test_password", "test%@:/?#password"])
def test_离线迁移支持其他启动目录和特殊字符密码(tmp_path, password):
    backend = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment.update(
        DATABASE_HOST="127.0.0.1",
        DATABASE_PORT="1",
        DATABASE_USERNAME="migration_test",
        DATABASE_PASSWORD=password,
        DATABASE_NAME="offline_test",
        SECRET_KEY="migration-tests-only-key-at-least-32-characters",
        SQL_ECHO="false",
        COOKIE_SECURE="false",
        PYTHONIOENCODING="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(backend / "alembic.ini"),
            "upgrade",
            "head",
            "--sql",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    sql = result.stdout
    assert password not in sql + result.stderr
    assert "ADD GENERATED ALWAYS AS IDENTITY" in sql
    assert "b27f4e9a6c10" in sql
    for table in ("users", "accounts", "categories", "transactions", "idempotency_keys"):
        assert f"CREATE TABLE {table}" in sql
    for index in (
        "idx_accounts_user",
        "idx_trans_user_date",
        "idx_trans_account",
        "idx_trans_category",
        "idx_idem_transaction",
    ):
        assert f"CREATE INDEX {index}" in sql
    for constraint in (
        "categories_money_type_check",
        "transactions_money_check",
        "transactions_money_type_check",
    ):
        assert f"CONSTRAINT {constraint} CHECK" in sql
    assert sql.count("ON DELETE RESTRICT") == 5
