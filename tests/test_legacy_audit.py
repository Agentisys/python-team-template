from __future__ import annotations

from pathlib import Path

from team_utils.legacy_audit import BLOCKER, INFO, JUNK, REVIEW, audit, main


def _tree(root: Path) -> None:
    """A small legacy folder with one of each problem the audit should find."""
    (root / "venv" / "Lib" / "site-packages" / "pandas").mkdir(parents=True)
    (root / "venv" / "pyvenv.cfg").write_text("home = C:\\Python38\n")
    (root / "venv" / "Lib" / "site-packages" / "pandas" / "__init__.py").write_text("")
    (root / ".git").mkdir()
    (root / "__pycache__").mkdir()
    (root / "sales_export.xlsx").write_bytes(b"PK\x03\x04")
    (root / "server.pfx").write_bytes(b"\x30\x82")
    (root / ".env").write_text("DB_PASSWORD=x\n")
    (root / "old.py.bak").write_text("")
    (root / "helpers.py").write_text("def total(rows):\n    return sum(rows)\n")
    (root / "etl.py").write_text(
        "import os, csv\n"
        "import pandas as pd\n"
        "import win32com.client\n"
        "from helpers import total\n"
        "SHARE = r'\\\\fileshare01\\finance$\\exports'\n"
        "OUT = 'C:\\\\scripts\\\\output'\n"
        "HOST = '10.20.4.15'\n"
        "LOCAL = '127.0.0.1'\n"
        "DB = 'sql01.corp.local'\n"
        "VERSION = '1.2.3'\n"
    )
    (root / "py2_job.py").write_text("import requests\nprint 'hello'\n")
    (root / "notes.txt").write_bytes("caf\xe9 on app01.contoso.com\n".encode("cp1252"))


def _details(result, level: str) -> list[str]:
    return [f"{f.path} {f.detail}" for f in result.findings if f.level == level]


def test_blockers_and_junk(tmp_path: Path) -> None:
    _tree(tmp_path)
    result = audit(tmp_path)
    blockers = " | ".join(_details(result, BLOCKER))
    for expected in ["venv/", ".git/", "sales_export.xlsx", "server.pfx", ".env"]:
        assert expected in blockers
    junk = " | ".join(_details(result, JUNK))
    assert "__pycache__/" in junk
    assert "old.py.bak" in junk
    assert result.blockers == 5


def test_environment_references(tmp_path: Path) -> None:
    _tree(tmp_path)
    review = " | ".join(_details(audit(tmp_path), REVIEW))
    assert "UNC path" in review
    assert "drive-letter path" in review
    assert "IP address: 10.20.4.15" in review
    assert "127.0.0.1" not in review
    assert "1.2.3" not in review
    assert "internal host name: sql01.corp.local" in review
    assert "contoso.com" not in review  # only with --internal-domain


def test_custom_internal_domain(tmp_path: Path) -> None:
    _tree(tmp_path)
    review = " | ".join(_details(audit(tmp_path, ("contoso.com",)), REVIEW))
    assert "internal host name: app01.contoso.com" in review


def test_info_encoding_and_python2(tmp_path: Path) -> None:
    _tree(tmp_path)
    info = " | ".join(_details(audit(tmp_path), INFO))
    assert "notes.txt not UTF-8" in info
    assert "py2_job.py does not parse as Python 3" in info


def test_imports_skip_stdlib_local_and_venv(tmp_path: Path) -> None:
    _tree(tmp_path)
    imports = audit(tmp_path).imports
    assert set(imports) == {"pandas", "pywin32", "requests"}
    assert imports["pandas"] == {"etl.py"}
    assert imports["requests"] == {"py2_job.py"}  # found even though py2 doesn't parse


def test_exit_codes(tmp_path: Path) -> None:
    clean = tmp_path / "clean"
    clean.mkdir()
    (clean / "job.py").write_text("import logging\n")
    assert main([str(clean)]) == 0

    dirty = tmp_path / "dirty"
    dirty.mkdir()
    _tree(dirty)
    assert main([str(dirty)]) == 1
    assert main([str(tmp_path / "missing")]) == 2
