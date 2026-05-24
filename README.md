# 🦉 owl · check

![CI](https://github.com/OwlsDontTalk/owlcheck/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-2-E92063?logo=pydantic&logoColor=white)
![pydantic-settings](https://img.shields.io/badge/pydantic--settings-2-E92063)
![License](https://img.shields.io/badge/License-MIT-yellow)
![PyPI](https://img.shields.io/pypi/v/owlcheck?color=006DAD&label=PyPI)

**Your Python service must not start with a broken environment.** `owlcheck` enforces that.

One call at the top of your application's entrypoint validates that every environment variable your code declares it needs is present and well-typed. The process either starts with a complete configuration or it does not start at all.

This eliminates a specific class of production failure: the service that boots cleanly, accepts traffic for ten minutes, then crashes the first time a code path reaches for `os.environ.get("STRIPE_SECRET")`. With `owlcheck`, that variable is checked before the first request — or the process exits before any request can arrive.

## Status

Early development. API is not yet stable. Requires `pydantic>=2`, `pydantic-settings>=2`, Python 3.10+.

## Installation

```bash
pip install owlcheck
```

## The canonical pattern

There is exactly one way to use `owlcheck`. This is by design.

```python
# main.py
from owlcheck import Settings
from pydantic import Field


class AppSettings(Settings):
    database_url: str = Field(..., alias="DATABASE_URL", description="Postgres DSN")
    stripe_secret: str = Field(..., alias="STRIPE_SECRET", description="Stripe API secret")
    debug: bool = Field(False, alias="DEBUG")


settings = AppSettings.load_or_exit()
```

That's the entire integration. After this line returns, `settings` is a validated, immutable record of your application's configuration. Import it anywhere:

```python
from main import settings

connect(settings.database_url)
```

If any required environment variable is missing or invalid, the process exits with code 1 and a log message that names the violated contract — before any handler, worker, or background task can run.

## What this enforces

* **No partial-config startup.** Validation runs before your application accepts any work. If something required is missing, the process fails immediately with a readable report; it does not run for ten minutes and crash at request time.
* **One source of truth.** Your `Settings` subclass *is* the schema. Scattered `os.environ.get(...)` calls in handlers, workers, and helpers are explicitly the failure mode `owlcheck` exists to prevent.
* **Aliased error messages.** Validation errors name the environment variable (the field's alias), not the Python attribute. Operators read `DATABASE_URL: missing (Postgres DSN)`, not `database_url: field required`.
* **Undeclared `.env` keys are surfaced.** Any variable in your `.env` file that isn't a declared field is reported at startup - that undeclared surface is the failure mode owlcheck exists to remove - and ones that look like a typo of a field name get a "did you mean" hint. (Ambient environment variables aren't pulled in; only keys actually in the file.) Every extra is then dropped so nothing undeclared reaches your code.
* **Per-field status log.** Each declared field is reported on startup as `provided` (from env or override) or `default`. You always know what configuration the process actually loaded.
* **Immutable after load.** Once `load_or_exit()` returns, the contract is frozen. Attempts to mutate `settings.x = ...` raise `ValidationError`. The configuration of a running process does not change under the code that depends on it.

## Why "one call"

The alternative — scattered `os.getenv("X")` checks across handlers, workers, and helpers — is a tax that compounds:

1. A contributor adds a feature that reads `os.getenv("NEW_FLAG")`. Code review does not catch it; nothing connects `NEW_FLAG` to the declared schema.
2. The feature ships. In production, `NEW_FLAG` is unset. The feature degrades silently in some flows, loudly in others. Nobody notices until a customer complains.
3. You spend an afternoon `grep`ing for every `os.getenv` and `os.environ.get` in the repo to figure out what the *actual* configuration surface of the service is.

`owlcheck` makes one canonical pattern strictly easier than every alternative. Declare every environment variable your service needs as a `Field` on your `Settings` subclass. Call `load_or_exit()` once in `main.py`. Use `settings.x` everywhere else. The schema is the contract; the call enforces it.

## Public API

| Symbol | Purpose |
| --- | --- |
| `Settings` | Base class. Subclass it; declare fields with `Field(alias=...)`. |
| `Settings.load_or_exit(**kw)` | The canonical entrypoint. Loads, validates, prints diagnostics; calls `sys.exit(1)` if anything is wrong. |
| `Settings.load(**kw)` | Same as above, but raises `ValidationError` instead of exiting. For callers that must handle the error themselves (rare). |
| `load(cls, **kw)` / `load_or_exit(cls, **kw)` | Functional forms for when you cannot subclass `Settings` (e.g., a third-party `BaseSettings` type passed in). |
| `clear_cache()` | Test helper. Drops cached `load()` results. Not for application code. |

## Design choices

* **Honest typing only.** If a field can be `None` at runtime, declare it `T | None`. `owlcheck` does not provide "soft optional" markers that lie to the type checker.
* **Library, not framework.** `owlcheck` does not configure logging for you. Configure your application's logging once; `owlcheck` writes to `logging.getLogger("owlcheck")` like any well-behaved library.
* **Immutable after load.** Once `load()` returns, the contract is frozen. See above.

## License

[MIT](LICENSE)
