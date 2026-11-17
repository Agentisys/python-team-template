"""Check that this machine is set up for the repo.

uv run team-doctor           # local checks
uv run team-doctor --azure   # also check Azure sign-in and Key Vault (needs --extra keyvault)
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from team_utils.config import REPO_ROOT, get_settings

OK, WARN, FAIL = "OK", "WARN", "FAIL"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def check_python() -> Check:
    wanted = (REPO_ROOT / ".python-version").read_text(encoding="utf-8").strip()
    running = f"{sys.version_info.major}.{sys.version_info.minor}"
    if running == wanted:
        return Check("Python version", OK, f"{platform.python_version()} (pinned {wanted})")
    return Check("Python version", FAIL, f"running {running}, repo pins {wanted}; use `uv run`")


def check_tool(tool: str, required: bool) -> Check:
    path = shutil.which(tool)
    if path:
        return Check(f"{tool} on PATH", OK, path)
    return Check(f"{tool} on PATH", FAIL if required else WARN, "not found")


def check_git_config() -> Check:
    git = shutil.which("git")
    if not git:
        return Check("git pull.rebase", WARN, "git not found")
    result = subprocess.run(  # noqa: S603 - fixed arguments, no user input
        [git, "config", "--get", "pull.rebase"], capture_output=True, text=True, check=False
    )
    if result.stdout.strip() == "true":
        return Check("git pull.rebase", OK, "true")
    return Check("git pull.rebase", WARN, "run: git config --global pull.rebase true")


def check_venv() -> Check:
    if Path(sys.prefix).resolve() == (REPO_ROOT / ".venv").resolve():
        return Check("Repo .venv in use", OK, sys.prefix)
    return Check("Repo .venv in use", WARN, f"running from {sys.prefix}; use `uv run`")


def check_env_mode() -> Check:
    settings = get_settings()
    if settings.use_key_vault:
        try:
            import azure.identity  # noqa: F401 - only checking it is installed
        except ImportError:
            return Check(
                "Secrets mode",
                WARN,
                "KEY_VAULT_URL is set but the Azure libraries are missing; "
                "run: uv sync --all-packages --extra keyvault",
            )
        return Check("Secrets mode", OK, f"Key Vault: {settings.key_vault_url}")
    return Check("Secrets mode", WARN, "local mode (KEY_VAULT_URL unset): secrets come from .env")


def check_azure() -> list[Check]:
    settings = get_settings()
    try:
        from azure.identity import DefaultAzureCredential
    except ImportError:
        return [
            Check(
                "Azure libraries",
                FAIL,
                "not installed; run: uv sync --all-packages --extra keyvault",
            )
        ]
    try:
        DefaultAzureCredential().get_token("https://vault.azure.net/.default")
    except Exception as exc:
        return [Check("Azure sign-in", FAIL, f"{type(exc).__name__}; try `az login`")]
    checks = [Check("Azure sign-in", OK, "token acquired for Key Vault")]

    if not settings.key_vault_url:
        checks.append(Check("Key Vault access", WARN, "KEY_VAULT_URL unset; skipped"))
        return checks
    try:
        from team_utils.vault import _client

        names = [p.name for p in _client(settings.key_vault_url).list_properties_of_secrets()]
        checks.append(Check("Key Vault access", OK, f"{len(names)} secret name(s) visible"))
    except Exception as exc:
        checks.append(Check("Key Vault access", FAIL, f"{type(exc).__name__}: check RBAC role"))
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check this machine is set up for the repo.")
    parser.add_argument("--azure", action="store_true", help="also check Azure and Key Vault")
    args = parser.parse_args(argv)

    checks = [
        check_python(),
        check_tool("uv", required=True),
        check_tool("git", required=True),
        check_tool("gitleaks", required=False),
        check_git_config(),
        check_venv(),
        check_env_mode(),
    ]
    if args.azure:
        checks.extend(check_azure())

    width = max(len(c.name) for c in checks)
    for c in checks:
        print(f"[{c.status:<4}] {c.name:<{width}}  {c.detail}")

    failed = sum(c.status == FAIL for c in checks)
    print(f"\n{len(checks)} checks, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
