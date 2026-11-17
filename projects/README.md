# Projects

Every project the team runs lives here, one folder each. A project is a small set of
related scheduled jobs, such as a nightly reconciliation or a set of daily reports, with its own
dependencies, tests, README and owner. All projects share this repository's lockfile, CI,
review rules and the `team_utils` package.

Why one repository for every project: one place to look, one set of review rules and
checks, and shared code without copying it. Split a project into its own repository only
if it grows into a long-lived application with its own release cycle or a different team.

## The projects

| Project | What it does | Owner |
| --- | --- | --- |
| [example-project](example-project/README.md) | Example: daily low-stock check. Delete once you have your own | `@your-org/python-team` |

Add a row when you add a project.

## Set up your machine

Once, after cloning (the [README](../README.md#quick-start) covers installing Git and uv):

```bash
uv sync --all-packages        # team_utils plus every project and its dependencies
uv run pre-commit install
uv run pytest                 # every project's tests, plus the shared ones
```

`--all-packages` matters: a plain `uv sync` installs only `team_utils`, not the projects.

## Work on one project

| Task | Command |
| --- | --- |
| Run one of its jobs | `uv run --package example-project projects/example-project/jobs/low_stock.py --help` |
| Run its tests | `uv run pytest projects/example-project` |
| Add a library it needs | `uv add --package example-project openpyxl` |
| Remove one | `uv remove --package example-project openpyxl` |
| Lint and format everything | `uv run ruff check --fix .` then `uv run ruff format .` |

`uv add --package <project>` adds the library to **that project's** `pyproject.toml` only,
and updates the shared `uv.lock`. Never add a project's library to the root
`pyproject.toml`, which is for `team_utils` alone.

## Add a project

1. **Create it.** One command makes the whole folder in the standard shape:

   ```bash
   uv run team-new-project finance-recon --description "Nightly bank reconciliation."
   ```

   Names are lowercase-kebab-case (`finance-recon`); the Python package inside is the
   snake_case version (`finance_recon`).
2. **Install it.** Run `uv lock`, then `uv sync --all-packages`, then
   `uv run pytest projects/finance-recon`.
3. **Fill in its README.** Owner, jobs, schedule, inputs, outputs, settings and secrets.
   Reviewers and on-call people read this first.
4. **Give it an owner.** Add `/projects/finance-recon/  @team-or-handle` to
   [`.github/CODEOWNERS`](../.github/CODEOWNERS), and a row to the table above.
5. **Add its libraries** with `uv add --package finance-recon <library>`.
6. **Write the real jobs and logic.** Rename `jobs/example_job.py`; put logic in
   `src/finance_recon/` with tests in `tests/`. Moving an existing script? Follow
   [Adding an existing script](../docs/adding-a-script.md).
7. **Open one pull request** for the new project.

`uv run pytest` checks that every project keeps the standard shape and has a CODEOWNERS
line, so a missing step fails CI rather than surprising someone later.

## What a project looks like

```text
projects/finance-recon/
  pyproject.toml           name, description, the libraries this project needs
  README.md                owner, jobs, schedule, inputs, outputs, settings, secrets
  jobs/                    runnable jobs: thin scripts ending in run_job(...)
    reconcile_bank.py
  src/finance_recon/       the project's logic, importable and tested
    __init__.py
    matching.py
  tests/                   pytest tests for src/finance_recon/
    test_matching.py
```

| Put it in | When it is… |
| --- | --- |
| `jobs/` | Something Task Scheduler runs: parse arguments, call the logic, write output |
| `src/<package>/` | Logic only this project uses |
| `src/team_utils/` (repository root) | Code two or more projects need. Move it there in its own pull request, with tests |
| `tests/` | Tests for this project's `src/` code |

Settings that aren't secret go in the root `.env.example`, prefixed with the project's
name (`FINANCE_RECON_INPUT_SHARE`). Secrets are always read with
`get_secret("finance-recon-bank-api-key")`: from `FINANCE_RECON_BANK_API_KEY` in `.env`
for now, from Key Vault once the team uses one, with no code change.

## Schedule a project's job

The server installs every project with `deploy\windows\deploy.ps1`. Register each job with
its project name:

```powershell
.\deploy\windows\register_task.ps1 -TaskName "Finance - reconcile bank" -Package finance-recon `
    -Script "projects\finance-recon\jobs\reconcile_bank.py" -At "02:00" -ServiceAccount "DOMAIN\svc-pyjobs$"
```

The task runs `uv run --frozen --no-dev --package finance-recon "projects\…\reconcile_bank.py"`.
Name tasks `<Project> - <job>` so they sort together. Task names can't contain
`\ / : * ? " < > |`.

## Removing the example project

Once your first real project exists, delete the example in one pull request:

1. Delete `projects/example-project/`.
2. Remove its line from `.github/CODEOWNERS` and its row from the table above.
3. Run `uv lock`, then `uv sync --all-packages`, then `uv run pytest`.
