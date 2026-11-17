# Security policy

## Reporting a problem

Found a leaked secret, a vulnerable dependency or anything that looks wrong? Tell the
team lead directly (**replace with a name or address**), never in a public channel or a
GitHub issue. For a leaked secret, **rotate it first**, then report.

## Rules this repo follows

The full list, with reasons, is in [docs/best-practices.md](docs/best-practices.md). In short:

- No secrets in Git. Scripts read them at run time with `team_utils.get_secret`, from a
  gitignored `.env` today and from Azure Key Vault once the team uses one.
- gitleaks scans every commit (pre-commit) and every pushed commit (CI).
- Every change to `main` goes through a pull request with review and green CI.
  Direct pushes, force pushes and deletion of `main` are blocked.
- Dependencies are locked in `uv.lock`; updates arrive as Dependabot pull requests and
  are reviewed like any other change.
- Scheduled jobs run as dedicated service accounts with only the access they need.
- AI coding assistants follow [AGENTS.md](AGENTS.md), and are used only where your
  agreements with clients allow them.

## If a secret was committed

1. Rotate the secret in its source system, and update it wherever the job reads it.
2. Remove it from the code in a normal pull request.
3. Ask the team lead whether history needs rewriting (`git filter-repo`). Rotation
   matters more, because clones and CI logs may already have the old value.
4. Note what happened and what changed so it does not repeat.
