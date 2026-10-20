import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from config import Settings


@pytest.fixture(autouse=True)
def clean_config_environment(monkeypatch):
    for key in list(os.environ):
        if key.lower() in Settings.model_fields:
            monkeypatch.delenv(key)


@pytest.fixture
def required_config():
    return {
        "database_host": "localhost",
        "database_username": "test_user",
        "database_password": "test_password",
        "database_name": "config_test",
        "secret_key": "test-config-secret-key-at-least-32-characters",
    }


def test_可选配置使用默认值(required_config):
    settings = Settings(_env_file=None, **required_config)
    assert settings.database_port == 5432
    assert settings.cookie_secure is False
    assert settings.sql_echo is False


@pytest.mark.parametrize(
    "value,expected", [("true", True), ("false", False), ("1", True), ("0", False)]
)
def test_布尔环境变量正确转换(required_config, monkeypatch, value, expected):
    monkeypatch.setenv("COOKIE_SECURE", value)
    monkeypatch.setenv("SQL_ECHO", value)
    settings = Settings(_env_file=None, **required_config)
    assert settings.cookie_secure is expected
    assert settings.sql_echo is expected


@pytest.mark.parametrize("key", ["COOKIE_SECURE", "SQL_ECHO"])
def test_错误布尔值在加载配置时拒绝(required_config, monkeypatch, key):
    monkeypatch.setenv(key, "not-a-boolean")
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, **required_config)
    assert key.lower() in {item["loc"][0] for item in error.value.errors()}


@pytest.mark.parametrize("port", ["1", "65535", "6543"])
def test_数据库端口从环境变量读取(required_config, monkeypatch, port):
    monkeypatch.setenv("DATABASE_PORT", port)
    assert Settings(_env_file=None, **required_config).database_port == int(port)


@pytest.mark.parametrize("port", ["0", "65536", "invalid"])
def test_无效端口在加载配置时拒绝(required_config, monkeypatch, port):
    monkeypatch.setenv("DATABASE_PORT", port)
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, **required_config)
    assert "database_port" in {item["loc"][0] for item in error.value.errors()}


@pytest.mark.parametrize(
    "field",
    ["secret_key", "database_host", "database_username", "database_password", "database_name"],
)
def test_缺少必填配置时拒绝启动(required_config, field):
    required_config.pop(field)
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, **required_config)
    assert field in {item["loc"][0] for item in error.value.errors()}


def test_空签名密钥在加载配置时拒绝(required_config):
    required_config["secret_key"] = ""
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, **required_config)
    assert "secret_key" in {item["loc"][0] for item in error.value.errors()}


def test_启动校验错误文本不暴露密钥():
    secret = "dummy-key"
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, secret_key=secret)
    assert secret not in str(error.value)
    assert "input_value" not in str(error.value)


def test_环境变量覆盖配置文件且忽略测试库字段(required_config, monkeypatch, tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(f"{key.upper()}={value}" for key, value in required_config.items())
        + "\nDATABASE_PORT=5433\nCOOKIE_SECURE=false\nTEST_DATABASE_NAME=other_test\n",
        encoding="utf-8",
    )
    from_file = Settings(_env_file=dotenv)
    assert from_file.database_name == "config_test"
    assert from_file.database_port == 5433
    assert from_file.cookie_secure is False
    monkeypatch.setenv("DATABASE_PORT", "6543")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    from_environment = Settings(_env_file=dotenv)
    assert from_environment.database_port == 6543
    assert from_environment.cookie_secure is True


def test_从其他目录启动时各模块使用同一配置(required_config, tmp_path):
    environment = os.environ.copy()
    environment.update({key.upper(): value for key, value in required_config.items()})
    environment.update(DATABASE_PORT="6543", COOKIE_SECURE="true", SQL_ECHO="true")
    backend = str(Path(__file__).resolve().parents[1])
    code = "\n".join(
        [
            "import sys",
            f"sys.path.insert(0, {backend!r})",
            "import config, main, database, auth",
            "from routers import users",
            "assert database.settings is config.settings is users.settings",
            "assert database.DATABASE_URL.port == 6543",
            "assert database.engine.echo is True",
            "assert users.settings.cookie_secure is True",
            "assert auth.SECRET_KEY == config.settings.secret_key",
            "assert database.DATABASE_URL.database == 'config_test'",
        ]
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
