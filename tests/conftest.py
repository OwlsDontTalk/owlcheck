"""Shared fixtures for the owlcheck test suite."""

from __future__ import annotations

import pytest

import owlcheck


@pytest.fixture(autouse=True)
def _isolate_cache() -> None:
    """Clear owlcheck's load cache before and after every test."""

    owlcheck.clear_cache()
    yield
    owlcheck.clear_cache()
