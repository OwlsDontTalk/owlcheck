"""Diagnostic log builders for owlcheck.

Not part of the public API. Imported only by :mod:`owlcheck.settings`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import ValidationError
    from pydantic_settings import BaseSettings


def log_validation_error(
    exc: ValidationError,
    model_cls: type[BaseSettings],
    logger: logging.Logger,
) -> None:
    """Log a readable summary of the violated configuration contract.

    Errors are mapped from internal field names back to their aliases so the
    output names the actual environment variable an operator would set, and
    the field's ``description`` is appended in parentheses when present so
    the reader sees both *what* is broken and *what it was for*.
    """

    issues: list[str] = []
    for error in exc.errors():
        loc = error.get("loc")
        if not loc:
            continue
        loc_key = str(loc[0])
        # pydantic-settings reports errors keyed by alias when one is set, so
        # try the field-name lookup first and fall back to alias matching.
        field = model_cls.model_fields.get(loc_key)
        if field is None:
            field = next(
                (f for f in model_cls.model_fields.values() if f.alias == loc_key),
                None,
            )
        alias = field.alias if field and field.alias else loc_key

        # Pydantic's default message for a missing required field is
        # "Field required"; "missing" reads more naturally in our context.
        if error.get("type") == "missing":
            msg = "missing"
        else:
            msg = error.get("msg", "invalid value")

        description = (field.description or "").strip() if field else ""
        suffix = f" ({description})" if description else ""

        issues.append(f"{alias}: {msg}{suffix}")

    if not issues:
        logger.error(
            "Process startup aborted: configuration validation failed: %s",
            exc,
        )
        return

    count = len(issues)
    noun = "variable" if count == 1 else "variables"
    verb = "is" if count == 1 else "are"
    header = (
        f"Process startup aborted: {count} environment {noun} required by "
        f"this application {verb} missing or invalid."
    )
    body = "\n".join(f" - {issue}" for issue in issues)
    logger.error("%s\n%s", header, body)


def log_field_status(settings: BaseSettings, logger: logging.Logger) -> None:
    """Log each declared field as ``provided`` (came from env/overrides) or ``default``."""

    lines: list[str] = []
    fields = settings.__class__.model_fields
    for name, field in fields.items():
        alias = field.alias or name
        description = (field.description or "No description provided.").strip()
        origin = "provided" if name in settings.model_fields_set else "default"
        lines.append(f" - {alias}: {origin}. {description}")
    joined = "\n".join(lines)
    logger.info("Configuration loaded successfully:\n%s", joined)


def log_additional_environment(
    settings: BaseSettings,
    logger: logging.Logger,
) -> None:
    """Warn about unknown variables captured by ``extra='allow'`` and clear them.

    With ``extra='allow'`` on the model, any key present in the ``.env`` file
    that does not correspond to a declared field ends up in ``model_extra``.
    We surface these as a warning (a common cause is a typo in the env file
    name) and then remove them so downstream code cannot accidentally rely on
    undeclared configuration.
    """

    extras = getattr(settings, "model_extra", None)
    if not extras:
        return
    extra_keys = sorted(str(key) for key in extras.keys())
    lines = "\n".join(f" - {key}" for key in extra_keys)
    logger.warning(
        "Additional environment variables detected and ignored:\n%s",
        lines,
    )
    extras.clear()
