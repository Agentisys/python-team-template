"""One way to get a secret, wherever the script runs.

    from team_utils import get_secret
    password = get_secret("report-db-password")

* KEY_VAULT_URL unset (the default) -> read the environment variable with the
  same name in UPPER_SNAKE_CASE (report-db-password -> REPORT_DB_PASSWORD),
  from the process environment or the gitignored .env file.
* KEY_VAULT_URL set -> read from Azure Key Vault using DefaultAzureCredential
  (a server's managed identity, or `az login` on a laptop). Needs the optional
  Azure libraries: uv sync --all-packages --extra keyvault

Moving to Key Vault later needs no code change: the secret names stay the same.

Secret values are never logged.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING

from team_utils.config import get_settings

if TYPE_CHECKING:
    from azure.keyvault.secrets import SecretClient


class SecretNotFoundError(LookupError):
    """Raised when a secret is missing, with a message that says where we looked."""


def env_var_name(secret_name: str) -> str:
    """Map a Key Vault secret name to its local-mode environment variable."""
    return secret_name.replace("-", "_").upper()


INSTALL_HINT = (
    "KEY_VAULT_URL is set but the Azure libraries are not installed. "
    "Run: uv sync --all-packages --extra keyvault"
)


@lru_cache(maxsize=4)
def _client(vault_url: str) -> SecretClient:
    # Imported lazily: the Azure libraries are an optional extra, only needed for Key Vault.
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
    except ImportError as exc:
        raise RuntimeError(INSTALL_HINT) from exc

    return SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())


def _is_not_found(exc: Exception) -> bool:
    try:
        from azure.core.exceptions import ResourceNotFoundError
    except ImportError:
        return False
    return isinstance(exc, ResourceNotFoundError)


def get_secret(name: str) -> str:
    """Return the secret called `name` (Key Vault naming: lowercase-with-dashes)."""
    settings = get_settings()

    if settings.use_key_vault:
        client = _client(settings.key_vault_url)
        try:
            value = client.get_secret(name).value
        except Exception as exc:
            if _is_not_found(exc):
                raise SecretNotFoundError(
                    f"Secret '{name}' not found in {settings.key_vault_url}"
                ) from exc
            raise
        if value is None:
            raise SecretNotFoundError(f"Secret '{name}' in {settings.key_vault_url} has no value")
        return value

    var = env_var_name(name)
    value = os.environ.get(var)
    if not value:  # missing or empty (an unfilled line copied from .env.example)
        raise SecretNotFoundError(
            f"Environment variable {var} is missing or empty. Add {var}=... to your .env "
            f"(or set KEY_VAULT_URL to read secrets from Azure Key Vault)."
        )
    return value
