import sys

import pytest

from team_utils.doctor import FAIL, check_azure


def test_doctor_azure_without_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "azure.identity", None)

    [check] = check_azure()

    assert check.status == FAIL
    assert "--extra keyvault" in check.detail


def test_env_mode_warns_when_key_vault_set_without_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    from team_utils.doctor import WARN, check_env_mode

    monkeypatch.setenv("KEY_VAULT_URL", "https://kv-test.vault.azure.net")
    monkeypatch.setitem(sys.modules, "azure.identity", None)

    check = check_env_mode()

    assert check.status == WARN
    assert "--extra keyvault" in check.detail
