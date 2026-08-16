"""
app/config.py 에 대한 단위 테스트

Settings 클래스의 기본값, allowed_origins_list 프로퍼티, 필수 필드 검증,
get_settings()의 캐싱(lru_cache) 동작을 검증한다.
"""
import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_MAX_TOKENS",
    "OPENAI_TEMPERATURE",
    "MASSIVE_API_KEY",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
]


class TestSettingsDefaults:
    def test_app_version_default(self):
        settings = Settings(_env_file=None, **_valid_required_kwargs())
        assert settings.app_version == "1.3.4"

    def test_server_defaults(self):
        settings = Settings(_env_file=None, **_valid_required_kwargs())
        assert settings.server_host == "0.0.0.0"
        assert settings.server_port == 8000
        assert settings.server_reload is False

    def test_log_level_default(self):
        settings = Settings(_env_file=None, **_valid_required_kwargs())
        assert settings.log_level == "DEBUG"

    def test_allowed_origins_default(self):
        settings = Settings(_env_file=None, **_valid_required_kwargs())
        assert settings.allowed_origins == "http://localhost:8080,https://api.qbit.o-r.kr"


class TestAllowedOriginsList:
    def test_splits_default_comma_separated_origins(self):
        settings = Settings(_env_file=None, **_valid_required_kwargs())
        origins = settings.allowed_origins_list
        assert origins == ["http://localhost:8080", "https://api.qbit.o-r.kr"]

    def test_strips_whitespace_around_origins(self):
        kwargs = _valid_required_kwargs()
        kwargs["allowed_origins"] = " http://a.com ,  http://b.com  "
        settings = Settings(_env_file=None, **kwargs)
        assert settings.allowed_origins_list == ["http://a.com", "http://b.com"]

    def test_single_origin(self):
        kwargs = _valid_required_kwargs()
        kwargs["allowed_origins"] = "http://only-one.com"
        settings = Settings(_env_file=None, **kwargs)
        assert settings.allowed_origins_list == ["http://only-one.com"]


class TestSettingsRequiredFields:
    def test_raises_when_required_field_missing(self, monkeypatch):
        for var in REQUIRED_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_raises_for_invalid_numeric_type(self, monkeypatch):
        for var in REQUIRED_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        kwargs = _valid_required_kwargs()
        kwargs["openai_max_tokens"] = "not-a-number"
        with pytest.raises(ValidationError):
            Settings(_env_file=None, **kwargs)

    def test_accepts_all_required_fields(self):
        settings = Settings(_env_file=None, **_valid_required_kwargs())
        assert settings.openai_api_key == "key"
        assert settings.db_host == "db-host"
        assert settings.db_port == 5432


class TestGetSettingsCaching:
    def test_get_settings_returns_settings_instance(self):
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_is_cached(self):
        first = get_settings()
        second = get_settings()
        assert first is second


def _valid_required_kwargs() -> dict:
    """Settings 생성에 필요한 필수 필드 값 모음 (env_file을 사용하지 않는 명시적 인스턴스화용)"""
    return {
        "openai_api_key": "key",
        "openai_model": "gpt-4o-mini",
        "openai_max_tokens": 1000,
        "openai_temperature": 0.7,
        "massive_api_key": "massive-key",
        "db_host": "db-host",
        "db_port": 5432,
        "db_name": "db-name",
        "db_user": "db-user",
        "db_password": "db-password",
    }