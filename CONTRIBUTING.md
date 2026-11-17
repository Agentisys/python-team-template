# How we work: the team Git SOP

Every change reaches `main` through a short-lived branch and a pull request with
green CI and one approval from a teammate, merged by squash. Nobody pushes to
`main`, and servers only ever deploy `main`.

## One-time machine setup

```bash
git config --global user.name "Your Name"
git config --global user.email "you@company.com"
git config --global pull.rebase true
git config --global fetch.prune true
git config --global rebase.autoStash true
git config --global init.defaultBranch main
git config --global core.autocrlf input     # Windows: true
```

Then in the repo: `uv sync --all-packages` and `uv run pre-commit install`.

## The daily loop

| Step | Command |
| --- | --- |
| 1. Start fresh | `git switch main` then `git pull` |
| 2. Branch | `git switch -c feat/short-description` |
| 3. Work and commit small | `git add -p` then `git commit -m "feat(report): add region filter"` |
| 4. Stay current (daily) | `git fetch` then `git rebase origin/main` |
| 5. Push and open a PR | `git push -u origin HEAD`, then open the PR on GitHub |
| 6. Address review | more commits on the same branch, `git push` |
| 7. Merge | author clicks **Squash and merge** after approval and green CI |
| 8. Clean up | `git switch main`, `git pull`, `git branch -d feat/short-description` |
| 9. Deploy | on the server: `deploy\windows\deploy.ps1` |

## Branch names

`feat/`, `fix/`, `chore/`, `docs/`, `hotfix/` followed by a few words with dashes.
One branch per change. A branch older than five working days gets split or finished.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`.

- Imperative, under 72 characters: `fix(team-utils): explain missing env var in error`
- The scope is the project folder for project changes: `feat(example-project): add region filter`.
  One pull request changes one project (plus `team_utils` only when it must).
- Body explains **why** when it is not obvious.
- One logical change per commit; formatting-only changes get their own commit.

## Pushing safely

- Rebase only your own unmerged branch.
- After a rebase of a pushed branch: `git push --force-with-lease`. Never plain `--force`.
- Never force-push or commit directly to `main` (pre-commit and the ruleset both block it).

## Pull requests

### Author

- Keep it under ~400 changed lines; split bigger work.
- Fill in the template: what, why, how tested, risk and rollback.
- Review your own diff first. Draft PRs are welcome for early feedback.

### Reviewer

Within one business day; the same day for `hotfix/` branches.

- Correct, including failure paths.
- No secrets, tokens, connection strings or real data.
- Uses `team_utils` (secrets, logging, `run_job`) instead of one-off code.
- Tests for new shared code; CI green.
- Dependency changes include `uv.lock` and a reason.
- Readable without the author in the room.

### Comments

Prefix optional remarks with `nit:`. Anything else blocks until resolved. Ask
questions rather than issuing verdicts.

### Merging

One approval, all conversations resolved, CI green, then the **author** squash-merges.
New commits after approval need re-approval.

While the team has a single member, an organisation admin may merge a green pull
request without the approval; direct pushes stay blocked. That exception ends the day
a second developer joins ([GitHub setup](docs/github-setup.md#ruleset-for-main)).

## Tests and CI

CI (`.github/workflows/ci.yml`) runs on every PR and push to `main`, on Linux and Windows:
`uv sync --locked --all-packages`, `ruff check`, `ruff format --check`, `pytest`, and a gitleaks scan of
every commit (rules in `.gitleaks.toml`).
Run the same locally before pushing:

```bash
uv run ruff check --fix .
uv run ruff format .
uv run pytest
```

## Dependencies

- Add to a project: `uv add --package <project> <pkg>`. Remove: `uv remove --package <project> <pkg>`.
  Shared tooling: `uv add --dev <pkg>`. Never add a project's library to the root `pyproject.toml`.
- Never edit `uv.lock` by hand; commit it with the `pyproject.toml` change.
- Dependabot opens weekly update PRs. Review them like any other PR.

## Issues

Every issue starts from a template (blank issues are off):

| Template | Use it for |
| --- | --- |
| **Migrate a script** | One existing script, from staging copy to production; carries the readiness checklist |
| **Change request** | A new job, a change to one, or a tooling improvement |
| **Bug report** | Something broke or behaves unexpectedly |
| **Standards exception** | A rule in [best practices](docs/best-practices.md) cannot be met for now |

Security problems never go in an issue: see [SECURITY.md](SECURITY.md).

## Hygiene

- No data exports, logs, binaries or `.env` files in Git (see `.gitignore`).
- Sample data stays small and fake.
- Delete merged branches (GitHub does it automatically); prune stale ones monthly.

See also: [SECURITY.md](SECURITY.md), [best practices](docs/best-practices.md) and
[adding an existing script](docs/adding-a-script.md).
