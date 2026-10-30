from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def project_root() -> Path:
    package_root = Path(__file__).resolve().parents[2]
    return (
        package_root.parent.parent
        if package_root.parent.name == "apps"
        else package_root
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(project_root() / ".env", Path.cwd() / ".env"),
        extra="ignore",
        hide_input_in_errors=True,
    )
    storage_root: Path = project_root() / ".local" / "files"
    model_cache: Path = project_root() / ".local" / "models"
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_revision: str = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://supportdesk:local-development-only@127.0.0.1:55432/supportdesk"
    redis_url: str = "redis://127.0.0.1:56379/0"
    session_secret: str = "development-only-never-use-in-production"
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    cookie_secure: bool = False
    demo_mode: bool = True
    llm_provider: Literal["fake", "compatible_http"] = "fake"
    fake_scenario: Literal[
        "normal", "slow", "invalid_citation", "drop", "timeout", "429"
    ] = "normal"
    ai_max_output_tokens: int = Field(default=800, ge=1, le=4096)
    ai_total_timeout_seconds: int = Field(default=90, ge=1, le=90)
    ai_daily_token_limit: int = Field(default=100000, ge=0)
    ai_provider_daily_token_limit: int = Field(default=200000, ge=0)
    ai_max_input_tokens: int = Field(default=6000, ge=512, le=16000)
    ai_max_concurrent: int = Field(default=1, ge=1, le=4)
    ai_max_queued: int = Field(default=10, ge=1, le=100)
    llm_connect_timeout_seconds: float = Field(default=5, gt=0, le=30)
    llm_read_timeout_seconds: float = Field(default=15, gt=0, le=90)
    llm_retry_after_max_seconds: int = Field(default=30, ge=1, le=60)
    public_live_ai_enabled: bool = False
    demo_daily_limit: int = Field(default=50, ge=1, le=1000)
    demo_active_limit: int = Field(default=50, ge=1, le=1000)
    upload_daily_limit: int = Field(default=20, ge=1, le=500)
    ingestion_max_queued: int = Field(default=5, ge=1, le=100)
    storage_max_bytes: int = Field(default=268435456, ge=10485760)
    trusted_proxies: list[str] = []
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_context_limit: int | None = Field(default=None, ge=1024)

    @model_validator(mode="after")
    def validate_runtime(self) -> "Settings":
        if not self.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("PostgreSQL with psycopg is required")
        from ipaddress import ip_network

        for proxy in self.trusted_proxies:
            if ip_network(proxy).prefixlen == 0:
                raise ValueError("Trust specific proxy addresses or private subnets")
        if (
            self.llm_context_limit
            and self.ai_max_output_tokens + 512 > self.llm_context_limit
        ):
            raise ValueError("Model context must leave room for application input")
        if not self.allowed_origins or any(
            urlsplit(origin).scheme not in {"http", "https"}
            or not urlsplit(origin).netloc
            or urlsplit(origin).path
            for origin in self.allowed_origins
        ):
            raise ValueError("Allowed origins must be exact HTTP origins without paths")
        if self.app_env == "production":
            if not self.cookie_secure or len(self.session_secret) < 32:
                raise ValueError(
                    "Production requires secure cookies and a strong secret"
                )
            if self.session_secret.startswith(("development-", "replace-", "change-")):
                raise ValueError("Development secret cannot be used in production")
            if any(
                not origin.startswith("https://") for origin in self.allowed_origins
            ):
                raise ValueError("Production origins must use HTTPS")
        if self.llm_provider == "compatible_http" and not all(
            [
                self.llm_base_url,
                self.llm_model,
                self.llm_api_key,
                self.llm_context_limit,
            ]
        ):
            raise ValueError("Live provider requires complete explicit configuration")
        if self.llm_base_url and urlsplit(self.llm_base_url).scheme not in {
            "http",
            "https",
        }:
            raise ValueError("Provider endpoint must use HTTP or HTTPS")
        if (
            self.app_env == "production"
            and self.llm_base_url
            and not self.llm_base_url.startswith("https://")
        ):
            raise ValueError("Production provider endpoint must use HTTPS")
        return self

    def cookie_name(self, audience: str) -> str:
        return f"{'__Host-' if self.cookie_secure else ''}sd_{audience}"

    def ai_enabled_for_public(self) -> bool:
        return (
            self.llm_provider == "fake"
            or self.app_env != "production"
            or self.public_live_ai_enabled
        )

    def input_allowance(self) -> int:
        return min(
            self.ai_max_input_tokens,
            (self.llm_context_limit or 8192) - self.ai_max_output_tokens,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
