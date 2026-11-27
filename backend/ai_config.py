from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).with_name(".env"),
        env_file_encoding="utf-8",
        env_prefix="AI_",
        extra="ignore",
        hide_input_in_errors=True,
    )

    enabled: bool = False
    api_key: SecretStr = SecretStr("")
    base_url: HttpUrl = HttpUrl("https://api.deepseek.com/v1")
    model: str = "deepseek-flash"
    output_mode: Literal["json_schema", "json_object"] = "json_object"
    token_field: Literal["max_completion_tokens", "max_tokens"] = "max_tokens"
    reasoning_effort: Literal["none", "low", "high", "max"] = "none"
    max_output_tokens: int = Field(default=800, ge=128, le=4096)
    batch_max_output_tokens: int = Field(default=2400, ge=128, le=4096)
    timeout_seconds: float = Field(default=90, ge=1, le=120)
    per_minute: int = Field(default=5, ge=1, le=60)
    per_day: int = Field(default=50, ge=1, le=1000)
    global_per_day: int = Field(default=200, ge=1, le=10000)
    concurrency: int = Field(default=2, ge=1, le=10)


ai_settings = AISettings()
