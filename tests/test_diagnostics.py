"""Tests for owlcheck's startup logging behaviour."""

from __future__ import annotations

import logging

import pytest
from pydantic import Field, ValidationError
from pydantic_settings import SettingsConfigDict

import owlcheck


class DiagSettings(owlcheck.Settings):
    model_config = SettingsConfigDict(
        env_file=None,
        case_sensitive=False,
        extra="allow",
        populate_by_name=True,
    )

    required_var: str = Field(..., alias="REQUIRED_VAR", description="A required thing.")
    optional_var: str = Field(
        "default-value", alias="OPTIONAL_VAR", description="An optional thing."
    )


def test_validation_error_message_uses_alias(monkeypatch, caplog):
    monkeypatch.delenv("REQUIRED_VAR", raising=False)
    with caplog.at_level(logging.ERROR, logger="owlcheck"):
        with pytest.raises(ValidationError):
            DiagSettings.load()
    assert "REQUIRED_VAR" in caplog.text
    assert "Configuration validation failed" in caplog.text


def test_field_status_logged_by_default(monkeypatch, caplog):
    monkeypatch.setenv("REQUIRED_VAR", "x")
    with caplog.at_level(logging.INFO, logger="owlcheck"):
        DiagSettings.load()
    assert "REQUIRED_VAR: provided" in caplog.text
    assert "OPTIONAL_VAR: default" in caplog.text
    assert "A required thing." in caplog.text


def test_field_status_can_be_disabled(monkeypatch, caplog):
    monkeypatch.setenv("REQUIRED_VAR", "x")
    with caplog.at_level(logging.INFO, logger="owlcheck"):
        DiagSettings.load(log_fields=False)
    assert "REQUIRED_VAR: provided" not in caplog.text
    assert "Configuration loaded successfully" not in caplog.text


def test_custom_logger_receives_diagnostics(monkeypatch):
    custom = logging.getLogger("test.owlcheck.custom")
    custom.setLevel(logging.DEBUG)
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Capture()
    custom.addHandler(handler)
    try:
        monkeypatch.setenv("REQUIRED_VAR", "x")
        DiagSettings.load(logger=custom)
    finally:
        custom.removeHandler(handler)

    messages = [r.getMessage() for r in records]
    assert any("REQUIRED_VAR" in m for m in messages)


def test_unknown_env_file_entries_emit_warning(monkeypatch, caplog, tmp_path):
    env_file = tmp_path / ".env.test"
    env_file.write_text("REQUIRED_VAR=hello\nUNKNOWN_TYPO_VAR=oops\n")

    class WithEnvFile(owlcheck.Settings):
        model_config = SettingsConfigDict(
            env_file=str(env_file),
            case_sensitive=False,
            extra="allow",
            populate_by_name=True,
        )

        required_var: str = Field(..., alias="REQUIRED_VAR")

    monkeypatch.delenv("REQUIRED_VAR", raising=False)
    monkeypatch.delenv("UNKNOWN_TYPO_VAR", raising=False)

    with caplog.at_level(logging.WARNING, logger="owlcheck"):
        settings = WithEnvFile.load()

    assert settings.required_var == "hello"
    # pydantic-settings lower-cases keys when case_sensitive=False; the
    # original name is still recognisable in the warning output.
    assert "unknown_typo_var" in caplog.text


def test_unknown_extras_cleared_after_warning(monkeypatch, caplog, tmp_path):
    env_file = tmp_path / ".env.test"
    env_file.write_text("REQUIRED_VAR=hello\nUNKNOWN_TYPO_VAR=oops\n")

    class WithEnvFile(owlcheck.Settings):
        model_config = SettingsConfigDict(
            env_file=str(env_file),
            case_sensitive=False,
            extra="allow",
            populate_by_name=True,
        )

        required_var: str = Field(..., alias="REQUIRED_VAR")

    monkeypatch.delenv("REQUIRED_VAR", raising=False)
    monkeypatch.delenv("UNKNOWN_TYPO_VAR", raising=False)

    settings = WithEnvFile.load()
    assert not settings.model_extra
