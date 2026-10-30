import pytest
from pydantic import ValidationError

from supportdesk.config import Settings


@pytest.fixture(autouse=True)
def isolated_llm_environment(monkeypatch):
    for name in (
        "LLM_PROVIDER",
        "LLM_BASE_URL",
        "LLM_API_KEY",
        "LLM_MODEL",
        "LLM_CONTEXT_LIMIT",
    ):
        monkeypatch.delenv(name, raising=False)


def test_production_cookie_origin_and_secret_validation():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", cookie_secure=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, allowed_origins=["https://example.invalid/path"])
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ai_total_timeout_seconds=91)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_provider="compatible_http")
    valid = Settings(
        _env_file=None,
        app_env="production",
        cookie_secure=True,
        session_secret="x" * 48,
        allowed_origins=["https://example.invalid"],
    )
    assert valid.cookie_name("staff") == "__Host-sd_staff"


def test_configuration_errors_hide_sensitive_values():
    secret = "sensitive-test-fixture-secret"
    with pytest.raises(ValidationError) as captured:
        Settings(_env_file=None, llm_provider="compatible_http", llm_api_key=secret)
    assert secret not in str(captured.value)
