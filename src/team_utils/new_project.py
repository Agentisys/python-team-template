"""Create a new project folder in projects/, in the shape every project here follows.

    uv run team-new-project finance-recon --description "Nightly bank reconciliation."

It creates projects/<name>/ with a pyproject.toml, a README to fill in, a package under
src/, a starter job in jobs/ and a test in tests/, then prints the next steps. It never
overwrites anything. See projects/README.md.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from team_utils.config import REPO_ROOT

NAME = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")


def module_name(name: str) -> str:
    """Project name (kebab-case) to Python package name (snake_case)."""
    return name.replace("-", "_")


def render(name: str, description: str) -> dict[str, str]:
    """Every file of a new project, keyed by its path inside projects/<name>/."""
    module = module_name(name)
    return {
        "pyproject.toml": f'''[project]
name = "{name}"
version = "0.1.0"
description = "{description}"
requires-python = ">=3.12"
dependencies = [
    "team-utils",   # shared code: settings, secrets, logging, run_job
]

[tool.uv.sources]
team-utils = {{ workspace = true }}

[build-system]
requires = ["uv_build>=0.11.32,<0.14.0"]
build-backend = "uv_build"

[tool.uv.build-backend]
module-name = "{module}"
''',
        "README.md": f"""# {name}

{description}

| | |
| --- | --- |
| **Owner** | TODO: team and GitHub handle |
| **Jobs** | `jobs/example_job.py` (rename it) |
| **Schedule** | TODO: when, and on which server |
| **Reads** | TODO: inputs, passed as arguments or settings |
| **Writes** | TODO: outputs |
| **Settings** | TODO: names added to `.env.example`, or "none" |
| **Secrets** | TODO: secret names (read with get_secret), or "none" |
| **Depends on** | `team-utils` |

## Run it

```bash
uv run --package {name} projects/{name}/jobs/example_job.py --help
```

## Schedule it (on the server)

```powershell
.\\deploy\\windows\\register_task.ps1 -TaskName "TODO" -Package {name} `
    -Script "projects\\{name}\\jobs\\example_job.py" -ServiceAccount "DOMAIN\\svc-pyjobs$"
```

## Test it

```bash
uv run pytest projects/{name}
```
""",
        f"src/{module}/__init__.py": f'"""{description}"""\n',
        "jobs/example_job.py": f'''"""Starter job for {name}: rename it, then replace main().

    uv run --package {name} \\
        projects/{name}/jobs/example_job.py
"""

from __future__ import annotations

import argparse
import logging

from team_utils import run_job

JOB_NAME = "{module}.example_job"
log = logging.getLogger(JOB_NAME)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="{description}")
    return parser.parse_args()


def main() -> None:
    parse_args()
    log.info("nothing to do yet")


if __name__ == "__main__":
    raise SystemExit(run_job(JOB_NAME, main))
''',
        f"tests/test_{module}.py": f'''from __future__ import annotations

import {module}


def test_package_imports() -> None:
    """Replace with tests for the logic in src/{module}/."""
    assert {module}.__doc__
''',
    }


def create(name: str, description: str, projects_dir: Path) -> Path:
    """Write the new project; refuse a bad name or an existing folder."""
    if not NAME.fullmatch(name):
        raise ValueError(f"'{name}' is not lowercase-kebab-case, e.g. finance-recon")
    target = projects_dir / name
    if target.exists():
        raise FileExistsError(f"{target} already exists")
    for relative, text in render(name, description).items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a new project in projects/.")
    parser.add_argument("name", help="lowercase-kebab-case, e.g. finance-recon")
    parser.add_argument("--description", default="TODO: one sentence on what this project does.")
    parser.add_argument("--projects-dir", type=Path, default=REPO_ROOT / "projects")
    args = parser.parse_args(argv)

    try:
        target = create(args.name, args.description.replace('"', "'"), args.projects_dir)
    except (ValueError, FileExistsError) as exc:
        print(f"Not created: {exc}")
        return 1

    print(f"Created {target}\n\nNext steps:")
    print("  1. uv lock, then uv sync --all-packages    # add it to the lockfile and install it")
    print(f"  2. uv run pytest projects/{args.name}      # the starter test passes")
    print(f"  3. Fill in projects/{args.name}/README.md (owner, schedule, settings, secrets)")
    print(f"  4. Add '/projects/{args.name}/  @owner' to .github/CODEOWNERS")
    print(f"  5. uv add --package {args.name} <library> for each dependency it needs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
