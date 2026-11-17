from pathlib import Path

import pytest

from team_utils.config import get_settings


def test_defaults_are_local_mode() -> None:
    settings = get_settings()
    assert settings.app_env == "local"
    assert settings.use_key_vault is False
    assert settings.log_level == "INFO"


def test_reads_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("KEY_VAULT_URL", "https://kv-test.vault.azure.net")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("LOG_DIR", str(tmp_path))

    settings = get_settings()

    assert settings.app_env == "prod"
    assert settings.use_key_vault is True
    assert settings.log_level == "DEBUG"
    assert settings.log_dir == tmp_path
