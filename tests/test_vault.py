import sys
from types import SimpleNamespace

import pytest

from team_utils import vault
from team_utils.vault import SecretNotFoundError, env_var_name, get_secret


def test_env_var_name() -> None:
    assert env_var_name("report-db-password") == "REPORT_DB_PASSWORD"


def test_local_mode_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPORT_DB_PASSWORD", "local-only-value")
    assert get_secret("report-db-password") == "local-only-value"


def test_local_mode_missing_secret_explains_fix() -> None:
    with pytest.raises(SecretNotFoundError, match="REPORT_DB_PASSWORD"):
        get_secret("report-db-password")


def test_key_vault_mode_uses_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEY_VAULT_URL", "https://kv-test.vault.azure.net")
    calls: list[str] = []

    class FakeClient:
        def get_secret(self, name: str) -> SimpleNamespace:
            calls.append(name)
            return SimpleNamespace(value="from-vault")

    monkeypatch.setattr(vault, "_client", lambda url: FakeClient())

    assert get_secret("report-db-password") == "from-vault"
    assert calls == ["report-db-password"]


def test_key_vault_without_extra_explains_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEY_VAULT_URL", "https://kv-test.vault.azure.net")
    # None in sys.modules makes `import azure.identity` raise ImportError.
    monkeypatch.setitem(sys.modules, "azure.identity", None)
    monkeypatch.setitem(sys.modules, "azure.keyvault.secrets", None)

    with pytest.raises(RuntimeError, match="uv sync --all-packages --extra keyvault"):
        get_secret("report-db-password")


def test_key_vault_missing_secret_raises_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEY_VAULT_URL", "https://kv-test.vault.azure.net")

    class FakeClient:
        def get_secret(self, name: str) -> SimpleNamespace:
            return SimpleNamespace(value=None)

    monkeypatch.setattr(vault, "_client", lambda url: FakeClient())

    with pytest.raises(SecretNotFoundError, match="has no value"):
        get_secret("report-db-password")
