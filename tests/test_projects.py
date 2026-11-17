"""Every project in projects/ follows the same shape, so anyone can find their way around.

The shape is described in projects/README.md; `uv run team-new-project <name>` creates it.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from team_utils.config import REPO_ROOT

PROJECTS = sorted(p for p in (REPO_ROOT / "projects").iterdir() if (p / "pyproject.toml").exists())


@pytest.mark.parametrize("project", PROJECTS, ids=lambda p: p.name)
def test_project_shape(project: Path) -> None:
    meta = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    name = meta["project"]["name"]
    module = meta["tool"]["uv"]["build-backend"]["module-name"]

    assert name == project.name, "the folder is named after the project"
    assert "team-utils" in meta["project"]["dependencies"], "every project uses team_utils"
    assert meta["tool"]["uv"]["sources"]["team-utils"] == {"workspace": True}
    assert (project / "src" / module / "__init__.py").exists(), "logic lives in src/<module>/"
    assert list((project / "jobs").glob("*.py")), "runnable jobs live in jobs/"
    assert list((project / "tests").glob("test_*.py")), "every project has tests"

    readme = (project / "README.md").read_text(encoding="utf-8")
    for field in ("**Owner**", "**Jobs**", "**Schedule**", "**Secrets**"):
        assert field in readme, f"README.md must say {field}"


@pytest.mark.parametrize("project", PROJECTS, ids=lambda p: p.name)
def test_project_has_a_code_owner(project: Path) -> None:
    codeowners = (REPO_ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert f"/projects/{project.name}/" in codeowners, "add the project to .github/CODEOWNERS"
