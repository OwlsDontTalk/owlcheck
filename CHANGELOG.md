# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2026-05-24

### Changed

- The undeclared-variable warning now adds a typo hint. owlcheck still surfaces
  every key in `.env` that isn't a declared field (that undeclared surface is
  the whole point), but for any that closely resembles a declared field's name
  it now appends the name it was likely mistyped from (`DATABAS_URL (did you
  mean DATABASE_URL?)`). Ambient environment variables remain out of scope here
  - only keys present in the file are extras. No API change.

## [0.2.0] - 2026-05-20

This release sharpens the package's single invariant — *one call at process
startup validates every declared environment variable; the process either
starts with a complete config or it does not start at all* — without
broadening the product. Docs, error output, and the loaded instance itself
are all aligned around enforcing that invariant.

### Changed

- **Validation-failure messages now name the violated contract.** The
  startup-abort log no longer reads `Configuration validation failed. Check
  environment variables:`. It now reads
  `Process startup aborted: N environment variable(s) required by this
  application are missing or invalid.`, followed by each variable with its
  declared `description` appended in parentheses for context.
- **Loaded `Settings` instances are immutable** (`model_config(frozen=True)`).
  Attempts to mutate `settings.x = ...` after `load()` returns raise
  `ValidationError`. The configuration of a running process should not change
  underneath the code that depends on it.
- **README rewritten around the startup-validation invariant.** Leads with
  the failure mode owlcheck eliminates; presents the canonical one-call
  pattern; removes alternative usage examples (FastAPI `Depends`, ad-hoc
  test helpers) that diluted the "one call at startup" message.

### Rejected

For self-discipline and future reference: these were considered for v0.2 and
deliberately *not* added, because each would dilute the single-invariant
positioning by introducing parallel checks that operate outside runtime
startup validation:

- `.env.example` generation from the schema.
- CLI commands (`owlcheck check`, `owlcheck diff`, etc.).
- Pre-commit / CI hooks that compare `.env` against the schema.
- Schema export to Markdown / JSON Schema.
- Cross-service config-drift detection.
- Secret-shape validation.
- Profile-based configs ("required in prod, optional in dev").

## [0.1.0] - 2026-05-19

### Added

- `owlcheck.Settings` base class — a thin subclass of `pydantic_settings.BaseSettings`
  with sensible defaults (`.env` auto-load, case-insensitive env var names,
  `populate_by_name=True`, unknown env-file keys surfaced as warnings).
- `owlcheck.load(cls, **kwargs)` — construct any `BaseSettings` subclass with
  diagnostics and a per-class singleton cache.
- `owlcheck.load_or_exit(cls, **kwargs)` — convenience wrapper that calls
  `sys.exit` on a `ValidationError`. Intended for application entrypoints.
- `owlcheck.clear_cache()` — drop cached `load` results (mostly useful in tests).
- Startup diagnostics: per-field `provided`/`default` status log, alias-keyed
  validation error messages, warnings about unknown variables in the `.env` file.
- Test suite covering caching, overrides, fail-fast behaviour, and logging.
