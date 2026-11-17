# GitHub setup

The settings that turn the rules in [CONTRIBUTING.md](../CONTRIBUTING.md) into rules
GitHub enforces. An admin does this once, then re-checks it with [Verify](#verify) after
any change. Menu names shift a little as GitHub updates its interface.

## First push

The pre-commit hook `no-commit-to-branch` blocks commits on `main`. For the very first
commit only, skip that one hook:

```powershell
git init -b main
git add -A
$env:SKIP = "no-commit-to-branch"; git commit -m "chore: initial import"; Remove-Item Env:SKIP
git remote add origin https://github.com/your-org/your-repo.git
git push -u origin main
```

From here on, every change goes through a pull request.

## Organisation

- [ ] The repository lives in the company organisation, is **private**, and is not in a
      personal account.
- [ ] The organisation requires two-factor authentication for every member.
- [ ] Two teams: `python-team` (the developers) and `python-team-leads` (one or two people).

## Access

*Settings → Collaborators and teams*

- [ ] `python-team`: **Write**. `python-team-leads`: **Admin**. Nobody else.
- [ ] `.github/CODEOWNERS` names those teams instead of individual usernames.

## Pull requests

*Settings → General → Pull Requests*

- [ ] Allow **squash merging** only; untick merge commits and rebase merging.
- [ ] Default squash commit message: **pull request title and description**.
- [ ] **Automatically delete head branches**: on.
- [ ] **Always suggest updating pull request branches**: on.

## Ruleset for `main`

*Settings → Rules → Rulesets → New branch ruleset*

- [ ] Name `main`, target **Default branch**, enforcement **Active**.
- [ ] **Restrict deletions** and **Block force pushes**.
- [ ] **Require linear history.**
- [ ] **Require a pull request before merging**, with:
  - [ ] Required approvals: **1**
  - [ ] Dismiss stale approvals when new commits are pushed
  - [ ] Require review from Code Owners
  - [ ] Require conversation resolution before merging
- [ ] **Require status checks to pass**: `tests (ubuntu-latest)`, `tests (windows-latest)` and
      `secrets scan`. The checks only appear in the list after CI has run once.
- [ ] **Bypass list**: empty. While only one person works in the repository, add
      **Organization admin** in mode **For pull requests only**, because GitHub never lets
      authors approve their own pull requests. Remove it the day a second developer joins.

## Security

*Settings → Code security*

- [ ] Dependency graph, Dependabot alerts and Dependabot security updates: on.
- [ ] Secret scanning and push protection: on, if your plan includes them. Without them,
      gitleaks on every commit and in CI covers the gap.

## Actions

*Settings → Actions → General*

- [ ] Allow only actions created by GitHub, pinned to a full-length commit SHA. CI is
      already written this way, which is why it installs uv with `pip`.
- [ ] Workflow permissions: **Read repository contents**.
- [ ] Do not allow Actions to create or approve pull requests.

## Tokens and keys

- [ ] Servers pull with a **read-only deploy key**, never a developer's personal token.
- [ ] Developers use Git Credential Manager (installed with Git for Windows) or SSH keys;
      no tokens in remote URLs.

## Verify

- [ ] `git push origin main` from a clone is **rejected**.
- [ ] A pull request with a failing test cannot be merged.
- [ ] A fake secret committed on a branch is caught by pre-commit, or by CI if the hook
      was skipped.
- [ ] Merged pull requests delete their branch.
