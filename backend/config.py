from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).with_name(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    database_host: str
    database_username: str
    database_password: str
    database_name: str
    database_port: int = Field(default=5432, ge=1, le=65535)
    secret_key: str = Field(min_length=1)
    cookie_secure: bool = False
    sql_echo: bool = False


settings = Settings()
