"""Tests for owlcheck.load, load_or_exit, caching, and overrides."""

from __future__ import annotations

import pytest
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

import owlcheck


class AppSettings(owlcheck.Settings):
    model_config = SettingsConfigDict(
        env_file=None,
        case_sensitive=False,
        extra="allow",
        populate_by_name=True,
    )

    database_url: str = Field(..., alias="DATABASE_URL")
    debug: bool = Field(False, alias="DEBUG")


def test_load_reads_required_field_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/test")
    settings = AppSettings.load()
    assert settings.database_url == "postgres://localhost/test"
    assert settings.debug is False


def test_load_missing_required_raises_validation_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        AppSettings.load()


def test_load_or_exit_calls_sys_exit_on_failure(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        AppSettings.load_or_exit()
    assert exc_info.value.code == 1


def test_load_or_exit_honours_custom_exit_code(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        AppSettings.load_or_exit(exit_code=42)
    assert exc_info.value.code == 42


def test_load_returns_cached_instance_on_repeated_calls(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/first")
    first = AppSettings.load()
    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/second")
    second = AppSettings.load()
    assert first is second
    assert second.database_url == "postgres://localhost/first"


def test_load_reload_true_bypasses_cache(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/first")
    first = AppSettings.load()
    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/second")
    second = AppSettings.load(reload=True)
    assert first is not second
    assert second.database_url == "postgres://localhost/second"


def test_overrides_take_precedence_over_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/from-env")
    settings = AppSettings.load(database_url="postgres://override")
    assert settings.database_url == "postgres://override"


def test_overrides_do_not_pollute_cache(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/env")
    _ = AppSettings.load(database_url="postgres://override")
    cached = AppSettings.load()
    assert cached.database_url == "postgres://localhost/env"


def test_each_subclass_has_independent_cache(monkeypatch):
    class WorkerSettings(owlcheck.Settings):
        model_config = SettingsConfigDict(
            env_file=None,
            case_sensitive=False,
            extra="allow",
        )

        worker_concurrency: int = Field(..., alias="WORKER_CONCURRENCY")

    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/db")
    monkeypatch.setenv("WORKER_CONCURRENCY", "8")
    app = AppSettings.load()
    worker = WorkerSettings.load()
    assert app.database_url == "postgres://localhost/db"
    assert worker.worker_concurrency == 8


def test_module_level_load_accepts_plain_basesettings(monkeypatch):
    class PlainSettings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=None,
            case_sensitive=False,
            extra="allow",
        )

        token: str = Field(..., alias="API_TOKEN")

    monkeypatch.setenv("API_TOKEN", "secret")
    settings = owlcheck.load(PlainSettings)
    assert settings.token == "secret"


def test_loaded_settings_are_immutable(monkeypatch):
    """After load() returns, the contract is locked — settings cannot be mutated."""
    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/locked")
    settings = AppSettings.load()
    with pytest.raises(ValidationError):
        settings.database_url = "postgres://other"
    # Verify the original value was not changed.
    assert settings.database_url == "postgres://localhost/locked"


def test_clear_cache_forces_next_load_to_re_read(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/first")
    first = AppSettings.load()
    owlcheck.clear_cache()
    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/second")
    second = AppSettings.load()
    assert first is not second
    assert second.database_url == "postgres://localhost/second"
