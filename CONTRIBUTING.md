# Contributing

owlcheck has a deliberately narrow scope. Reading this before opening a PR will save us both time.

## What gets merged

- Bug fixes against the documented behaviour. Open an issue with a reproducer first.
- Documentation and integration recipes. Real recipes from real production use are the most useful contribution right now.
- Performance, packaging, and CI improvements.
- Tests covering behaviour the current suite misses.

## What usually won't

Features outside the single invariant (one call at startup, full config or the process doesn't start). Things like CLI commands, `.env.example` generation, schema export, profile-based configs, or loading from external secret stores are out of scope by design. If a PR adds one of these it will likely be closed with an explanation.

If you have a feature idea that you think fits the invariant, open an issue or a Discussion first, before writing code.

## Development setup

```bash
git clone https://github.com/OwlsDontTalk/owlcheck
cd owlcheck
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
ruff check .
```

## Commit messages

Conventional prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`) preferred, not enforced.

## Releases

Tag-triggered: pushing a `v*` tag builds and publishes to PyPI via Trusted Publisher (OIDC). Maintainer only.
```
