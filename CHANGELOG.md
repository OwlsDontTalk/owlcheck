# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
