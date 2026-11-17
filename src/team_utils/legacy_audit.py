"""Audit a legacy script folder before any of it goes into Git. Changes nothing.

    uv run team-legacy-audit C:/staging/old-scripts
    uv run team-legacy-audit C:/staging/old-scripts --internal-domain corp.contoso.com

Run it on a staging COPY (see docs/adding-a-script.md). It reports:

  BLOCKER  must not be committed: old virtual environments, .git/.svn history,
           credential files, data exports, binaries, files over 500 KB
  JUNK     safe to delete: __pycache__, *.pyc, logs, backups, Office lock files
  REVIEW   hard-coded environment details to turn into settings or arguments:
           UNC paths, drive-letter paths, IP addresses, internal host names
  INFO     files that are not UTF-8, files that do not parse as Python 3
           (usually Python 2), and the third-party packages the scripts import

Secrets are gitleaks' job, not this tool's:
    gitleaks dir <folder> -c .gitleaks.toml --redact -v

The report names servers and paths, so keep it out of Git and out of chat.
Exit code is 1 while any BLOCKER remains.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

BLOCKER, JUNK, REVIEW, INFO = "BLOCKER", "JUNK", "REVIEW", "INFO"
MAX_BYTES = 500 * 1024  # same limit as the check-added-large-files pre-commit hook

_HISTORY_DIRS = {".git", ".svn", ".hg"}
_JUNK_DIRS = {"__pycache__", ".ipynb_checkpoints", ".pytest_cache", ".mypy_cache", ".idea"}
_CREDENTIAL_SUFFIXES = {".pem", ".pfx", ".p12", ".key", ".ppk", ".kdbx", ".jks", ".rdp"}
_CREDENTIAL_NAMES = {".netrc", ".pgpass", "credentials.json", "token.json", "id_rsa", "id_ed25519"}
_DATA_SUFFIXES = {
    ".csv", ".xls", ".xlsx", ".xlsm", ".accdb", ".mdb", ".db", ".sqlite", ".sqlite3",
    ".pkl", ".parquet", ".pbix", ".zip", ".7z",
}  # fmt: skip
_BINARY_SUFFIXES = {".exe", ".dll", ".msi", ".pyd", ".so", ".whl"}
_JUNK_SUFFIXES = {".pyc", ".pyo", ".log", ".bak", ".old", ".orig", ".tmp"}
_JUNK_NAMES = {"thumbs.db", "desktop.ini", ".ds_store"}
_TEXT_SUFFIXES = {
    ".py", ".pyw", ".bat", ".cmd", ".ps1", ".vbs", ".sh", ".ini", ".cfg", ".conf",
    ".config", ".json", ".yaml", ".yml", ".xml", ".toml", ".txt", ".sql", ".ipynb",
}  # fmt: skip

_UNC = re.compile(r"\\{2,}[A-Za-z0-9][\w.$-]*(?:\\{1,2}[\w$.-]+)+")
_DRIVE = re.compile(r"(?<![\w\\])[A-Za-z]:(?:\\{1,2}|/)[\w.$-]+(?:(?:\\{1,2}|/)[\w.$-]+)*")
_IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
_INTERNAL_SUFFIXES = ("local", "corp", "lan", "internal", "intranet")
_IMPORT_FALLBACK = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_]\w*)", re.MULTILINE)

# Import name -> PyPI name, where they differ. Anything else: PyPI name = import name.
PYPI_NAMES = {
    "PIL": "pillow",
    "cv2": "opencv-python",
    "yaml": "pyyaml",
    "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    "dotenv": "python-dotenv",
    "jwt": "pyjwt",
    "Crypto": "pycryptodome",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "MySQLdb": "mysqlclient",
    "OpenSSL": "pyopenssl",
    "serial": "pyserial",
    "attr": "attrs",
    "win32com": "pywin32",
    "win32api": "pywin32",
    "win32con": "pywin32",
    "win32file": "pywin32",
    "pythoncom": "pywin32",
    "pywintypes": "pywin32",
}


@dataclass(frozen=True)
class Finding:
    level: str
    path: str
    detail: str


@dataclass
class Audit:
    findings: list[Finding]
    imports: dict[str, set[str]]  # PyPI name -> scripts that import it

    @property
    def blockers(self) -> int:
        return sum(f.level == BLOCKER for f in self.findings)


def _classify_file(path: Path, size: int) -> tuple[str, str] | None:
    name, suffix = path.name.lower(), path.suffix.lower()
    if name.startswith(".env") and name != ".env.example":
        return BLOCKER, "environment file with real values; move secrets to Key Vault"
    if suffix in _CREDENTIAL_SUFFIXES or name in _CREDENTIAL_NAMES:
        return BLOCKER, "credential or key file; move to Key Vault or a cert store"
    if suffix in _DATA_SUFFIXES:
        return BLOCKER, "data or archive file; keep out of Git (use a small fake sample)"
    if suffix in _BINARY_SUFFIXES:
        return BLOCKER, "binary; install it as a dependency instead of committing it"
    if suffix in _JUNK_SUFFIXES or name in _JUNK_NAMES or name.startswith("~$"):
        return JUNK, "generated, backup or temp file; delete"
    if size > MAX_BYTES:
        return BLOCKER, f"{size // 1024} KB is over the 500 KB limit; is it data?"
    return None


def _scan_text(rel: str, text: str, internal: tuple[str, ...]) -> list[Finding]:
    found: list[Finding] = []
    host = re.compile(
        r"\b[\w-]+(?:\.[\w-]+)*\.(?:" + "|".join(re.escape(s) for s in internal) + r")\b",
        re.IGNORECASE,
    )
    patterns = [
        (_UNC, "UNC path"),
        (_DRIVE, "drive-letter path"),
        (_IPV4, "IP address"),
        (host, "internal host name"),
    ]
    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern, label in patterns:
            for match in pattern.finditer(line):
                value = match.group(0)
                if label == "IP address" and (
                    value.startswith(("127.", "0.")) or any(int(o) > 255 for o in value.split("."))
                ):
                    continue
                found.append(Finding(REVIEW, f"{rel}:{lineno}", f"{label}: {value[:80]}"))
    return found


def _third_party_imports(text: str, local_modules: set[str]) -> tuple[set[str], bool]:
    """Return (top-level third-party import names, parses_as_python3)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        names = set(_IMPORT_FALLBACK.findall(text))
        parsed = False
    else:
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
        parsed = True
    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    return {n for n in names if n not in stdlib and n not in local_modules}, parsed


def audit(root: Path, internal_domains: tuple[str, ...] = ()) -> Audit:
    root = root.resolve()
    findings: list[Finding] = []
    imports: dict[str, set[str]] = defaultdict(set)
    internal = _INTERNAL_SUFFIXES + tuple(d.lstrip(".") for d in internal_domains)

    python_files: list[tuple[Path, str]] = []  # scanned after the walk, see below

    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        for d in list(dirnames):
            sub = here / d
            rel = sub.relative_to(root).as_posix() + "/"
            if (sub / "pyvenv.cfg").exists():
                findings.append(Finding(BLOCKER, rel, "virtual environment; delete it"))
            elif d.lower() == "site-packages":
                findings.append(Finding(BLOCKER, rel, "installed packages; delete them"))
            elif d in _HISTORY_DIRS:
                findings.append(
                    Finding(BLOCKER, rel, "old version-control history; do not carry it over")
                )
            elif d in _JUNK_DIRS:
                findings.append(Finding(JUNK, rel, "generated folder; delete"))
            else:
                continue
            dirnames.remove(d)  # don't descend into anything already reported

        for f in filenames:
            path = here / f
            rel = path.relative_to(root).as_posix()
            size = path.stat().st_size
            if verdict := _classify_file(path, size):
                findings.append(Finding(verdict[0], rel, verdict[1]))
                continue
            if path.suffix.lower() not in _TEXT_SUFFIXES:
                continue

            raw = path.read_bytes()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("cp1252", errors="replace")
                findings.append(Finding(INFO, rel, "not UTF-8 (likely cp1252); re-save as UTF-8"))
            findings.extend(_scan_text(rel, text, internal))

            if path.suffix.lower() in {".py", ".pyw"}:
                python_files.append((path, text))

    # Only modules that live in the folder itself count as local; anything inside a
    # skipped venv or site-packages was never walked, so it can't hide a real dependency.
    local_modules = {p.stem for p, _ in python_files} | {
        p.parent.name for p, _ in python_files if p.name == "__init__.py"
    }
    for path, text in python_files:
        rel = path.relative_to(root).as_posix()
        names, parsed = _third_party_imports(text, local_modules)
        if not parsed:
            findings.append(Finding(INFO, rel, "does not parse as Python 3 (Python 2 or broken)"))
        for name in names:
            imports[PYPI_NAMES.get(name, name)].add(rel)

    order = {BLOCKER: 0, JUNK: 1, REVIEW: 2, INFO: 3}
    findings.sort(key=lambda f: (order[f.level], f.path))
    return Audit(findings, dict(imports))


def render(result: Audit, root: Path) -> str:
    lines = [f"Legacy audit of {root}", ""]
    for level in (BLOCKER, JUNK, REVIEW, INFO):
        items = [f for f in result.findings if f.level == level]
        lines.append(f"== {level} ({len(items)})")
        lines.extend(f"  {f.path}  {f.detail}" for f in items)
        lines.append("")
    lines.append(f"== Third-party imports ({len(result.imports)})")
    for pkg, scripts in sorted(result.imports.items(), key=lambda kv: kv[0].lower()):
        lines.append(f"  {pkg:<24} {', '.join(sorted(scripts))}")
    if result.imports:
        lines += [
            "",
            "  Pin the versions that work today. On the server, with the python.exe the task runs:",
            "    <python.exe> -m pip show <package>",
            '  then in the repo:  uv add "<package>==<version>"',
        ]
    lines += ["", f"{result.blockers} blocker(s)."]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit a legacy script folder before it goes into Git. Changes nothing."
    )
    parser.add_argument("folder", type=Path, help="staging copy of the legacy folder")
    parser.add_argument(
        "--internal-domain",
        action="append",
        default=[],
        help="your internal DNS suffix, e.g. corp.contoso.com (repeatable)",
    )
    args = parser.parse_args(argv)

    if not args.folder.is_dir():
        print(f"{args.folder} is not a folder.")
        return 2
    result = audit(args.folder, tuple(args.internal_domain))
    print(render(result, args.folder.resolve()))
    return 1 if result.blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
