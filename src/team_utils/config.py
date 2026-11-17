"""Non-secret settings, read once from environment variables.

Settings come from the process environment first, then from a local `.env`
file if one exists (developer convenience only; never committed). Secrets do
NOT belong here: use `team_utils.vault.get_secret` for those.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# src/team_utils/config.py -> repo root is three levels up.
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """Everything a script needs to know about where it is running."""

    app_env: str
    """`local`, `dev` or `prod`. Only used for logging and sanity checks."""

    key_vault_url: str | None
    """e.g. https://kv-yourteam-prod.vault.azure.net. Unset = secrets from env vars / .env."""

    log_level: str
    log_dir: Path

    @property
    def use_key_vault(self) -> bool:
        return bool(self.key_vault_url)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build settings once per process. Tests call `get_settings.cache_clear()`."""
    load_dotenv(REPO_ROOT / ".env", override=False)

    log_dir = Path(os.environ.get("LOG_DIR") or REPO_ROOT / "logs")
    return Settings(
        app_env=os.environ.get("APP_ENV", "local"),
        key_vault_url=os.environ.get("KEY_VAULT_URL") or None,
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        log_dir=log_dir,
    )
