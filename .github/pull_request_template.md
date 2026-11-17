## What and why

<!-- One or two sentences: what changes, and why it is needed. Link the issue if there is one. -->

## How I tested it

<!-- Commands you ran and what you checked. e.g. `uv run pytest`, ran the job against sample data. -->

## Risk and rollback

<!-- What could break, who would notice, and how to undo it (usually: revert this PR and redeploy). -->

## Author checklist

- [ ] Branch is up to date with `main`
- [ ] `uv run ruff check .` and `uv run pytest` pass locally
- [ ] No secrets, tokens, connection strings or real data in the diff
- [ ] New or changed shared code in `team_utils` has tests
- [ ] Dependency changes made with `uv add` / `uv remove`, and `uv.lock` is included
- [ ] New dependency: why it is needed, and the [checks](../docs/best-practices.md#dependencies) answered below
- [ ] New or changed access (database, share, mailbox, Azure role): smallest permission that works
- [ ] Project README or docs updated if behaviour changed

## Reviewer checklist

- [ ] Does what the description says, including failure paths
- [ ] Uses `team_utils` helpers (secrets, logging, `run_job`) rather than one-off code
- [ ] Readable by someone who was not in the room
