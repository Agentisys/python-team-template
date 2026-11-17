"""Shared test fixtures for every project: each test starts with clean settings, env and logging."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from team_utils import config, vault
from team_utils.logging_setup import reset_logging_for_tests

_ENV_VARS = [
    "APP_ENV",
    "KEY_VAULT_URL",
    "LOG_LEVEL",
    "LOG_DIR",
    "REPORT_DB_PASSWORD",
]


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    # Never let a developer's real .env leak into tests.
    monkeypatch.setattr(config, "load_dotenv", lambda *a, **k: False)
    config.get_settings.cache_clear()
    vault._client.cache_clear()
    reset_logging_for_tests()
    yield
    config.get_settings.cache_clear()
    reset_logging_for_tests()
