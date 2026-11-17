# Instructions for AI coding agents

These rules apply to any AI coding assistant working in this repo (GitHub Copilot or
others). Humans: this is also a short summary of how we work.

## Environment

- This is a uv project. Run everything with `uv run ...`. Never call `pip`, never
  activate a venv by hand, never edit `uv.lock` directly.
- Add or remove dependencies only with `uv add --package <project> <pkg>` /
  `uv remove --package <project> <pkg>` (`--dev` for tooling). Explain why in the PR.
- Python version is pinned in `.python-version`.

## Code

- The team's work lives in `projects/<project>/`: jobs in `jobs/`, the project's logic in
  `src/<package>/`, tests in `tests/`, and a README with owner and schedule. Code two or
  more projects need goes in `src/team_utils/` with tests in `tests/`.
  New project: `uv run team-new-project <name>`. Rules and reasons: `docs/best-practices.md`.
- Install with `uv sync --all-packages`. Add a library to one project with
  `uv add --package <project> <library>`, never to the root `pyproject.toml`.
- Scheduled jobs end with `raise SystemExit(run_job("<name>", main))`.
- Use `logging`, not `print`, in `src/`. Get secrets only through `team_utils.get_secret`.
- Never hardcode passwords, tokens, connection strings or server credentials.
  Never print or log a secret value.

## Safety

- Do not read, print or modify `.env`, `*.pem`, `*.pfx` or anything under `secrets/`.
- Do not run commands that reach the internet (curl, wget, pip download, git clone of
  new repos) unless the developer explicitly asks.
- Do not push, merge, force-push, or change branch protection. Humans do that.
- Do not touch `deploy/` or `.github/` without being asked.

## Before saying a task is done

1. `uv run ruff check --fix .` and `uv run ruff format .`
2. `uv run pytest`
3. Summarise what changed and anything you were unsure about.
