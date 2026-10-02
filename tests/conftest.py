"""Isolate tests from the developer's application environment."""

import os

import pytest


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in os.environ:
        if key.startswith("PARALLAX_") and key != "PARALLAX_TEST_DATABASE_URL":
            monkeypatch.delenv(key)
