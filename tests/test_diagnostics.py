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
    assert "Process startup aborted" in caplog.text


def test_validation_error_includes_field_description(monkeypatch, caplog):
    monkeypatch.delenv("REQUIRED_VAR", raising=False)
    with caplog.at_level(logging.ERROR, logger="owlcheck"):
        with pytest.raises(ValidationError):
            DiagSettings.load()
    # The field description is appended so an operator sees what the
    # missing variable was supposed to do.
    assert "A required thing." in caplog.text
    # "missing" should replace pydantic's default "Field required" wording.
    assert "REQUIRED_VAR: missing" in caplog.text


def test_validation_error_header_counts_violations(monkeypatch, caplog):
    class TwoRequired(owlcheck.Settings):
        model_config = SettingsConfigDict(
            env_file=None,
            case_sensitive=False,
            extra="allow",
            populate_by_name=True,
        )

        first: str = Field(..., alias="FIRST", description="first var")
        second: str = Field(..., alias="SECOND", description="second var")

    monkeypatch.delenv("FIRST", raising=False)
    monkeypatch.delenv("SECOND", raising=False)
    with caplog.at_level(logging.ERROR, logger="owlcheck"):
        with pytest.raises(ValidationError):
            TwoRequired.load()
    assert "2 environment variables required by this application are missing" in caplog.text


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


def test_typo_like_extra_emits_warning(monkeypatch, caplog, tmp_path):
    # DATABAS_URL is one character off DATABASE_URL: an actual typo.
    env_file = tmp_path / ".env.test"
    env_file.write_text("DATABASE_URL=real\nDATABAS_URL=oops\n")

    class WithEnvFile(owlcheck.Settings):
        model_config = SettingsConfigDict(
            env_file=str(env_file),
            case_sensitive=False,
            extra="allow",
            populate_by_name=True,
        )

        database_url: str = Field(..., alias="DATABASE_URL")

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABAS_URL", raising=False)

    with caplog.at_level(logging.WARNING, logger="owlcheck"):
        settings = WithEnvFile.load()

    assert settings.database_url == "real"
    assert "databas_url" in caplog.text
    # The warning points at the variable it was likely mistyped from.
    assert "DATABASE_URL" in caplog.text


def test_undeclared_env_key_warns_without_typo_hint(monkeypatch, caplog, tmp_path):
    # AWS_REGION in .env is undeclared config, nothing like the declared field:
    # it is still surfaced (that's the leak owlcheck exists to catch), just
    # without a "did you mean" hint.
    env_file = tmp_path / ".env.test"
    env_file.write_text("DATABASE_URL=real\nAWS_REGION=us-east-1\n")

    class WithEnvFile(owlcheck.Settings):
        model_config = SettingsConfigDict(
            env_file=str(env_file),
            case_sensitive=False,
            extra="allow",
            populate_by_name=True,
        )

        database_url: str = Field(..., alias="DATABASE_URL")

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)

    with caplog.at_level(logging.WARNING, logger="owlcheck"):
        settings = WithEnvFile.load()

    assert "aws_region" in caplog.text
    assert "did you mean" not in caplog.text
    assert not settings.model_extra


def test_ambient_env_var_is_not_an_extra(monkeypatch, caplog):
    # A variable that lives only in the ambient environment (never in a .env
    # file) does not enter model_extra, so it is neither warned about nor cleared.
    class AmbientSettings(owlcheck.Settings):
        model_config = SettingsConfigDict(
            env_file=None,
            case_sensitive=False,
            extra="allow",
            populate_by_name=True,
        )

        database_url: str = Field(..., alias="DATABASE_URL")

    monkeypatch.setenv("DATABASE_URL", "real")
    monkeypatch.setenv("SOME_AMBIENT_THING", "x")

    with caplog.at_level(logging.WARNING, logger="owlcheck"):
        settings = AmbientSettings.load()

    assert "some_ambient_thing" not in caplog.text
    assert not settings.model_extra
