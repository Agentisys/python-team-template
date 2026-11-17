# python-team-template

A starter repository for a team's Python scripts and scheduled jobs. Every project lives
here in its own folder, and every change goes through a reviewed pull request with
automatic checks. Built on:

- **uv** for the Python version, virtual environments and locked dependencies
- **GitHub** pull requests, with CI on Windows and Linux on every change
- **Secret scanning** on every commit, so passwords and keys never reach Git
- **Windows Task Scheduler** for running jobs on servers, deployed only from `main`

## Quick start

1. **Install Git and uv** (once per machine). Windows, in PowerShell:

   ```powershell
   winget install --id Git.Git -e
   winget install --id astral-sh.uv -e
   winget install --id Gitleaks.Gitleaks -e     # secret scanner, used when adding scripts
   ```

   macOS: `brew install git uv gitleaks`. Open a new terminal afterwards.

2. **Set up Git** (once per machine): the commands are in
   [CONTRIBUTING.md](CONTRIBUTING.md#one-time-machine-setup).

3. **Clone and install**

   ```bash
   git clone https://github.com/your-org/python-team-template.git
   cd python-team-template
   uv sync --all-packages        # Python, team_utils and every project
   uv run pre-commit install     # checks that run on every commit
   ```

   uv downloads the right Python version itself; you don't need to install Python.

4. **Check it works.** Both should end with no failures.

   ```bash
   uv run team-doctor
   uv run pytest
   ```

5. **Run the example job**

   ```bash
   uv run --package example-project projects/example-project/jobs/low_stock.py --help
   ```

## How the repo is laid out

| Path | What it holds |
| --- | --- |
| `projects/` | **Your projects**, one folder each: jobs, logic, tests, README. See [projects/README.md](projects/README.md) |
| `src/team_utils/` | Shared code every project uses: settings, secrets, logging, the job wrapper and the team commands |
| `tests/` | Tests for `team_utils`, the docs and the project layout |
| `deploy/windows/` | Server scripts: deploy `main`, register a scheduled task |
| `docs/` | [Adding an existing script](docs/adding-a-script.md), [best practices](docs/best-practices.md), [GitHub setup](docs/github-setup.md) |
| `.github/` | CI, Dependabot, code owners, pull request and issue templates |

Root files: `pyproject.toml` (workspace, ruff and pytest settings), `uv.lock` (exact
versions, never edited by hand), `.python-version`, `.env.example` (setting names, no
values), `.gitleaks.toml` (secret-scan rules), `.pre-commit-config.yaml`.

## Daily workflow

Every change, however small, follows the same loop. Details in [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
git switch main                              # start from the latest main
git pull
git switch -c feat/short-description         # one branch per change
# ...edit, then check your work:
uv run ruff check --fix .
uv run ruff format .
uv run pytest
git add -p                                   # choose what goes in the commit
git commit -m "feat(example-project): add region filter"
git push -u origin HEAD                      # then open a pull request on GitHub
```

A teammate reviews, CI must be green, then the author clicks **Squash and merge**.
Nobody pushes to `main` directly.

## Secrets

Scripts never contain passwords, keys or connection strings. They ask for them by name:

```python
from team_utils import get_secret

password = get_secret("finance-db-password")
```

- **Now:** the value comes from `FINANCE_DB_PASSWORD` in a `.env` file that is never
  committed (copy `.env.example` to `.env` and fill it in). On a server, the `.env` lives
  in the repo folder, readable only by the job's service account and admins.
- **Later (recommended):** set `KEY_VAULT_URL`, and the same call reads from Azure Key
  Vault. No code changes, but every install then needs the Azure libraries:
  `uv sync --all-packages --extra keyvault` on laptops, and `deploy.ps1 -KeyVault` on
  servers. A plain `uv sync` removes them again.

## Commands

| Task | Command |
| --- | --- |
| Install or update everything | `uv sync --all-packages` |
| Create a project | `uv run team-new-project <name>` |
| Add a library to a project | `uv add --package <project> <library>` |
| Lint, then format | `uv run ruff check --fix .` then `uv run ruff format .` |
| Run the tests | `uv run pytest` |
| Run every commit check | `uv run pre-commit run --all-files` |
| Check your machine | `uv run team-doctor` |
| Audit an old script folder | `uv run team-legacy-audit <folder>` |
| Scan a folder for secrets | `gitleaks dir <folder> -c .gitleaks.toml --redact -v` |

## First-time setup (for whoever creates the repository)

This repository is a template. After copying it into your own GitHub organisation:

1. Replace `your-org` and `python-team-template` (your organisation and repository
   names) in the clone URL above and in `.github/ISSUE_TEMPLATE/config.yml`.
2. Replace `@your-org/python-team` and `@your-org/python-team-leads` in
   `.github/CODEOWNERS` and `projects/example-project/README.md` with your GitHub teams.
3. Work through [docs/github-setup.md](docs/github-setup.md): teams, the `main` ruleset,
   secret scanning, Actions settings.
4. Say who receives security reports in [SECURITY.md](SECURITY.md).
5. Replace `DOMAIN\svc-pyjobs$` in the examples with your service account once you have one.
6. Once your first real project exists, delete the example
   ([how](projects/README.md#removing-the-example-project)).
