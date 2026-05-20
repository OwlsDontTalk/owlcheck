# 🦉 owl · check

![CI](https://github.com/OwlsDontTalk/owlcheck/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-2-E92063?logo=pydantic&logoColor=white)
![pydantic-settings](https://img.shields.io/badge/pydantic--settings-2-E92063)
![License](https://img.shields.io/badge/License-MIT-yellow)
![PyPI](https://img.shields.io/pypi/v/owlcheck?label=PyPI&color=006DAD)

Fail-fast validation of environment-based configuration for Python applications.

`owlcheck` is a small ergonomics layer on top of [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/). It loads your environment-driven settings on startup, prints a readable report of what was supplied vs. defaulted, warns when your `.env` file contains unknown variables, and aborts the process with a clear error when something required is missing.

The owl watches silently; it only speaks up when something is wrong.

## Status

Early development — API is not yet stable. Pinned to `pydantic>=2`, `pydantic-settings>=2`, Python 3.10+.

## Installation

```bash
pip install owlcheck
```

## Usage

### Plain script / CLI

```python
from owlcheck import Settings
from pydantic import Field


class AppSettings(Settings):
    database_url: str = Field(..., alias="DATABASE_URL", description="Postgres DSN")
    debug: bool = Field(False, alias="DEBUG", description="Enable verbose logging")


settings = AppSettings.load_or_exit()

print(settings.database_url)
```

If `DATABASE_URL` is missing, the process exits with code 1 and a readable log of what was wrong.

### FastAPI

```python
from fastapi import FastAPI, Depends
from typing import Annotated

settings = AppSettings.load_or_exit()  # at module import time, fails fast on bad env


def get_settings() -> AppSettings:
    return AppSettings.load()  # cached after first call


app = FastAPI()


@app.get("/health")
def health(s: Annotated[AppSettings, Depends(get_settings)]):
    return {"db": s.database_url, "debug": s.debug}
```

### Tests

```python
def test_something():
    s = AppSettings.load(database_url="sqlite:///:memory:", debug=True)
    # Overrides bypass the cache entirely, so other tests are unaffected.
```

For full isolation between tests, clear the cache:

```python
import owlcheck

@pytest.fixture(autouse=True)
def _reset_owlcheck():
    owlcheck.clear_cache()
    yield
    owlcheck.clear_cache()
```

## What you get

* **Fail-fast on startup.** `load_or_exit()` calls `sys.exit(1)` with a readable summary if required env vars are missing or invalid.
* **Per-field status log.** On a successful load, each declared field is logged as `provided` (from env or overrides) or `default`, alongside its description.
* **Typo warnings.** Unknown variables in your `.env` file are surfaced as a warning, then cleared from the model so downstream code cannot accidentally rely on them.
* **Aliased error messages.** Validation errors are reported against the env var name (the field's alias), not the Python attribute name.
* **Per-class cache.** Multiple `Settings` subclasses can coexist without sharing state.
* **Pluggable logger.** Diagnostics go to `logging.getLogger("owlcheck")` by default; pass `logger=...` to redirect.

## Public API

```python
from owlcheck import Settings, load, load_or_exit, clear_cache
```

| Symbol | Purpose |
| --- | --- |
| `Settings` | Base class. Subclass it and declare fields with `Field(alias=...)`. |
| `Settings.load(**kw)` | Class-bound shortcut for `load(cls, **kw)`. |
| `Settings.load_or_exit(**kw)` | Class-bound shortcut for `load_or_exit(cls, **kw)`. |
| `load(cls, *, reload=False, log_fields=True, logger=None, **overrides)` | Construct any `BaseSettings` subclass with diagnostics and caching. |
| `load_or_exit(cls, *, exit_code=1, **kwargs)` | Like `load`, but calls `sys.exit` on `ValidationError`. |
| `clear_cache()` | Drop all cached `load` results. Mostly useful in tests. |

## Design choices

* **Honest typing only.** If a field can be `None` at runtime, declare it as `T | None`. `owlcheck` does not provide "soft optional" markers that lie to the type checker. This keeps `mypy`/`pyright` reliable and avoids surprise `AttributeError`s in production.
* **Library, not framework.** `owlcheck` does not configure logging for you. Configure your application's logging once, then `owlcheck` writes to `logging.getLogger("owlcheck")` like any well-behaved library.
* **No magic globals.** The cache lives at module level inside `owlcheck`, keyed by the concrete subclass. You can opt out with `reload=True` or `clear_cache()`.

## License

[MIT](LICENSE)
