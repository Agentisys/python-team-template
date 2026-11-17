from __future__ import annotations

from pathlib import Path

import pytest

from team_utils.new_project import create, main, module_name, render


def test_module_name_is_snake_case() -> None:
    assert module_name("finance-recon") == "finance_recon"


def test_create_writes_every_file(tmp_path: Path) -> None:
    target = create("finance-recon", "Nightly bank reconciliation.", tmp_path)
    files = sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file())
    assert files == [
        "README.md",
        "jobs/example_job.py",
        "pyproject.toml",
        "src/finance_recon/__init__.py",
        "tests/test_finance_recon.py",
    ]
    pyproject = (target / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "finance-recon"' in pyproject
    assert 'module-name = "finance_recon"' in pyproject
    assert "team-utils = { workspace = true }" in pyproject


def test_generated_python_compiles() -> None:
    for path, text in render("finance-recon", "Nightly bank reconciliation.").items():
        if path.endswith(".py"):
            compile(text, path, "exec")


@pytest.mark.parametrize("bad", ["Finance", "finance_recon", "1finance", "finance-", ""])
def test_rejects_names_that_are_not_kebab_case(tmp_path: Path, bad: str) -> None:
    with pytest.raises(ValueError, match="kebab-case"):
        create(bad, "x", tmp_path)


def test_never_overwrites(tmp_path: Path) -> None:
    create("finance-recon", "x", tmp_path)
    with pytest.raises(FileExistsError):
        create("finance-recon", "x", tmp_path)
    assert main(["finance-recon", "--projects-dir", str(tmp_path)]) == 1
