"""Diagnostic log builders for owlcheck.

Not part of the public API. Imported only by :mod:`owlcheck.settings`.
"""

from __future__ import annotations

import difflib
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
    """Warn about undeclared variables found in the ``.env`` file, then drop them.

    With ``extra='allow'`` on the model, any key in the ``.env`` file that does
    not match a declared field lands in ``model_extra``. (Ambient environment
    variables do not - pydantic-settings only surfaces keys actually present in
    the file.) Every one of those is configuration owlcheck cannot vouch for:
    either a variable you meant to declare and didn't, or a typo. We surface all
    of them - that undeclared surface is exactly what this library exists to
    eliminate - and for any that closely resemble a declared field we append the
    name it was likely mistyped from. Then every extra is cleared so downstream
    code cannot rely on undeclared configuration.
    """

    extras = getattr(settings, "model_extra", None)
    if not extras:
        return

    # Map each declared name (alias and field name, lower-cased to match how
    # pydantic-settings stores extras under case_sensitive=False) back to the
    # alias we'd show an operator.
    declared: dict[str, str] = {}
    for name, field in settings.__class__.model_fields.items():
        alias = field.alias or name
        declared.setdefault(alias.lower(), alias)
        declared.setdefault(name.lower(), alias)

    lines: list[str] = []
    for key in sorted(str(key) for key in extras):
        match = difflib.get_close_matches(key.lower(), declared, n=1, cutoff=0.8)
        if match and match[0] != key.lower():
            lines.append(f" - {key} (did you mean {declared[match[0]]}?)")
        else:
            lines.append(f" - {key}")

    extras.clear()

    logger.warning(
        "Undeclared variables found in .env (declare them or remove them):\n%s",
        "\n".join(lines),
    )
