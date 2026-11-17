"""Every relative link and #anchor in the repo's Markdown must resolve.

Runs in CI with the other tests, so moving or renaming a doc cannot silently break
the links that point at it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from team_utils.config import REPO_ROOT

_SKIP_DIRS = {".git", ".venv", "node_modules", ".pytest_cache", ".ruff_cache"}
_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
_FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*$", re.MULTILINE)


def _markdown_files() -> list[Path]:
    return sorted(p for p in REPO_ROOT.rglob("*.md") if not _SKIP_DIRS.intersection(p.parts))


def _slug(heading: str) -> str:
    """GitHub's anchor for a heading: lowercase, punctuation dropped, spaces to dashes."""
    text = re.sub(r"[`*_]|\[([^\]]*)\]\([^)]*\)", r"\1", heading.strip().lower())
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def _anchors(path: Path) -> set[str]:
    text = _FENCE.sub("", path.read_text(encoding="utf-8"))
    return {_slug(h) for h in _HEADING.findall(text)}


def _links(path: Path) -> list[str]:
    text = _FENCE.sub("", path.read_text(encoding="utf-8"))
    text = re.sub(r"`[^`\n]*`", "", text)  # links inside inline code are examples
    return [
        link
        for link in _LINK.findall(text)
        if not link.startswith(("http://", "https://", "mailto:"))
    ]


@pytest.mark.parametrize(
    "doc", _markdown_files(), ids=lambda p: p.relative_to(REPO_ROOT).as_posix()
)
def test_relative_links_resolve(doc: Path) -> None:
    broken = []
    for link in _links(doc):
        path, _, anchor = link.partition("#")
        target = (doc.parent / path).resolve() if path else doc
        if not target.exists():
            broken.append(f"{link} (no such file)")
        elif anchor and target.suffix == ".md" and anchor not in _anchors(target):
            broken.append(f"{link} (no heading #{anchor})")
    assert not broken, "broken links:\n  " + "\n  ".join(broken)


def _checkboxes(text: str) -> list[str]:
    """Checkbox lines with Markdown links reduced to their text (issues can't follow them)."""
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("- [ ]")]
    return [re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line) for line in lines]


def test_migration_template_matches_readiness_checklist() -> None:
    """The issue template carries a copy of the readiness checklist; keep them identical."""
    doc = (REPO_ROOT / "docs/best-practices.md").read_text(encoding="utf-8")
    checklist = doc[doc.index("## Readiness checklist") :]
    template = (REPO_ROOT / ".github/ISSUE_TEMPLATE/migrate-script.md").read_text(encoding="utf-8")
    part3 = template[template.index("## 3. Production readiness") :]
    assert _checkboxes(part3) == _checkboxes(checklist)


# ---------------------------------------------------------------- code examples

_PY_BLOCK = re.compile(r"^([ \t]*)```python\n(.*?)^\1```", re.MULTILINE | re.DOTALL)


def _python_blocks(path: Path) -> list[str]:
    import textwrap

    return [textwrap.dedent(block) for _, block in _PY_BLOCK.findall(path.read_text("utf-8"))]


@pytest.mark.parametrize(
    "doc",
    [p for p in _markdown_files() if _python_blocks(p)],
    ids=lambda p: p.relative_to(REPO_ROOT).as_posix(),
)
def test_python_examples_compile(doc: Path) -> None:
    """Every ```python block in the docs and skills is at least valid Python."""
    for number, block in enumerate(_python_blocks(doc), start=1):
        compile(block, f"{doc.name} block {number}", "exec")


# ---------------------------------------------------------------- config files

_JSON_CONFIGS = [".vscode/extensions.json", ".vscode/settings.json"]


@pytest.mark.parametrize("name", _JSON_CONFIGS)
def test_editor_config_is_valid_json(name: str) -> None:
    """A typo in a VS Code config fails silently in the editor; catch it here instead."""
    import json

    text = (REPO_ROOT / name).read_text(encoding="utf-8")
    text = re.sub(r"(?m)^\s*//.*$", "", text)  # JSONC: whole-line comments
    text = re.sub(r"\s+//[^\n\"]*$", "", text, flags=re.MULTILINE)  # trailing comments
    json.loads(text)
