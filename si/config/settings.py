"""Environment settings. Secrets come from the environment or `.env`, never from the repo."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

SendMode = Literal["test", "live"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("SI_DATABASE_URL", "DATABASE_URL")
    )
    offers_dir: Path = Path("offers")

    # ADR-0007: anything other than "live" is test mode, including unset.
    send_mode: SendMode = "test"
    only_to: Annotated[list[str], NoDecode] = Field(
        default_factory=list, validation_alias=AliasChoices("SI_ONLY_TO", "ONLY_TO")
    )

    anthropic_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("SI_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")
    )
    model_judgment: str = "claude-opus-5-5"
    model_bulk: str = "claude-haiku-5-5"
    gemini_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("SI_GEMINI_API_KEY", "GEMINI_API_KEY")
    )
    gemini_model: str = "gemini-2.5-flash"

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    imap_host: str | None = None
    imap_port: int = 993
    imap_user: str | None = None
    imap_password: SecretStr | None = None

    dkim_selectors: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["default", "google", "zoho", "selector1", "selector2", "k1"]
    )

    @field_validator("send_mode", mode="before")
    @classmethod
    def _fail_closed(cls, value: object) -> str:
        if isinstance(value, str) and value.strip().lower() == "live":
            return "live"
        return "test"

    @field_validator("only_to", "dkim_selectors", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("only_to")
    @classmethod
    def _lower(cls, value: list[str]) -> list[str]:
        return [item.lower() for item in value]

    @property
    def test_mode(self) -> bool:
        return self.send_mode != "live"


def load_settings() -> Settings:
    return Settings()
