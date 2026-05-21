"""Public :class:`Settings` base class and loader functions for owlcheck."""

from __future__ import annotations

import logging
import sys
from typing import Any, TypeVar

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from owlcheck._diagnostics import (
    log_additional_environment,
    log_field_status,
    log_validation_error,
)

_DEFAULT_LOGGER = logging.getLogger("owlcheck")

T = TypeVar("T", bound=BaseSettings)

# Singleton cache keyed by concrete subclass. Each Settings subclass has its
# own entry, so projects with multiple Settings classes (e.g. AppSettings,
# WorkerSettings) do not share state.
_CACHE: dict[type[BaseSettings], BaseSettings] = {}


def load(
    cls: type[T],
    *,
    reload: bool = False,
    log_fields: bool = True,
    logger: logging.Logger | None = None,
    **overrides: Any,
) -> T:
    """Construct ``cls`` from the environment with diagnostics and caching.

    Args:
        cls: Any :class:`pydantic_settings.BaseSettings` subclass (typically
            a subclass of :class:`owlcheck.Settings`).
        reload: If ``True``, bypass the cache and re-read the environment.
        log_fields: If ``True`` (default), log each declared field as
            ``provided`` or ``default`` after a successful load.
        logger: Logger to receive diagnostics. Defaults to the ``owlcheck``
            logger.
        **overrides: Field values passed directly to the model constructor.
            Calls that include overrides bypass the cache entirely; this is
            the recommended path for tests. Pydantic-settings magic kwargs
            such as ``_env_file`` are accepted here too.

    Returns:
        A validated instance of ``cls``.

    Raises:
        pydantic.ValidationError: When required environment variables are
            missing or invalid. The error is logged with field aliases
            before being re-raised.
    """

    active_logger = logger or _DEFAULT_LOGGER

    if overrides:
        return _build(cls, active_logger, log_fields, **overrides)

    if not reload and cls in _CACHE:
        return _CACHE[cls]  # type: ignore[return-value]

    instance = _build(cls, active_logger, log_fields)
    _CACHE[cls] = instance
    return instance


def load_or_exit(
    cls: type[T],
    *,
    exit_code: int = 1,
    **kwargs: Any,
) -> T:
    """Like :func:`load`, but call :func:`sys.exit` on validation failure.

    Designed for application entrypoints so the caller does not have to write
    ``try/except ValidationError`` boilerplate.
    """

    try:
        return load(cls, **kwargs)
    except ValidationError:
        print(
            f"[owlcheck] Process startup aborted: environment is incomplete "
            f"(exit code {exit_code}). See logs above for the violated "
            f"contract.",
            file=sys.stderr,
        )
        sys.exit(exit_code)


def clear_cache() -> None:
    """Drop all cached :func:`load` results.

    Useful in tests that want each call to read a fresh environment without
    relying on the ``reload=True`` kwarg.
    """

    _CACHE.clear()


def _build(
    cls: type[T],
    logger: logging.Logger,
    verbose: bool,
    **overrides: Any,
) -> T:
    try:
        instance = cls(**overrides)
    except ValidationError as exc:
        log_validation_error(exc, cls, logger)
        raise
    if verbose:
        log_field_status(instance, logger)
    log_additional_environment(instance, logger)
    return instance


class Settings(BaseSettings):
    """Base class for environment-driven application settings.

    A thin subclass of :class:`pydantic_settings.BaseSettings` with the
    defaults most applications want:

    * reads from a ``.env`` file if one is present in the working directory,
    * env var names are case-insensitive,
    * unknown variables in ``.env`` are surfaced as a warning rather than
      silently ignored.

    Subclass and declare your fields, then load on startup::

        from owlcheck import Settings
        from pydantic import Field

        class AppSettings(Settings):
            database_url: str = Field(..., alias="DATABASE_URL")
            debug: bool = Field(False, alias="DEBUG")

        settings = AppSettings.load_or_exit()

    Override :attr:`model_config` in your subclass to change the defaults.
    Note that pydantic does not deep-merge ``model_config`` across the
    inheritance chain; to keep the owlcheck defaults while adding your own,
    spread them explicitly::

        class AppSettings(Settings):
            model_config = SettingsConfigDict(
                **Settings.model_config,
                env_prefix="APP_",
            )
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
        # Accept overrides passed to load(**kwargs) by the Python field name
        # in addition to the alias. Tests in particular rely on this.
        populate_by_name=True,
        # The configuration of a running process should not change after
        # startup. ``frozen=True`` makes any mutation attempt on the loaded
        # instance raise ``ValidationError``, enforcing the invariant
        # structurally rather than by convention.
        frozen=True,
    )

    @classmethod
    def load(cls: type[T], **kwargs: Any) -> T:
        """Class-bound shortcut for :func:`owlcheck.load`."""

        # The bare name `load` here resolves to the module-level function via
        # Python's LEGB rule; the classmethod name lives on the class, not in
        # this function's local scope.
        return load(cls, **kwargs)

    @classmethod
    def load_or_exit(cls: type[T], **kwargs: Any) -> T:
        """Class-bound shortcut for :func:`owlcheck.load_or_exit`."""

        return load_or_exit(cls, **kwargs)
