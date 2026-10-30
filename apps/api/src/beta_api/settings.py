from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """API configuration. Environment variables use the ``BETA_`` prefix (see .env.example)."""

    model_config = SettingsConfigDict(env_prefix="BETA_", env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    var_dir: Path = Path("var")
    public_base_url: str = "http://localhost:8000"
    renderer_url: str | None = None
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "ANTHROPIC_API_KEY", "BETA_ANTHROPIC_API_KEY", "anthropic_api_key"
        ),
    )
    planner_model: str | None = None
    director_model: str | None = None
    classifier_model: str | None = None
    use_hold_classifier: bool = False
    max_upload_bytes: int = 15 * 1024 * 1024
    host: str = "127.0.0.1"
    port: int = 8000

    @field_validator(
        "anthropic_api_key",
        "renderer_url",
        "planner_model",
        "director_model",
        "classifier_model",
        mode="before",
    )
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @property
    def media_dir(self) -> Path:
        return self.var_dir / "media"

    @property
    def db_path(self) -> Path:
        return self.var_dir / "beta.sqlite3"
