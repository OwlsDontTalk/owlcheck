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
    """Log a readable summary of missing or invalid environment variables.

    Errors are mapped from internal field names back to their aliases so the
    output names the actual environment variable a user would set.
    """

    issues: list[str] = []
    for error in exc.errors():
        loc = error.get("loc")
        if not loc:
            continue
        field_name = str(loc[0])
        field = model_cls.model_fields.get(field_name)
        alias = field.alias if field and field.alias else field_name
        issues.append(f"{alias}: {error.get('msg', 'invalid value')}")

    if not issues:
        logger.error("Configuration validation failed: %s", exc)
        return

    joined = "\n".join(f" - {issue}" for issue in issues)
    logger.error(
        "Configuration validation failed. Check environment variables:\n%s",
        joined,
    )


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
