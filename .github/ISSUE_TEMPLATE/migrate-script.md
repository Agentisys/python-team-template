---
name: Migrate a script
about: Move one existing scheduled script into this repo and into production
title: "Migrate: <script name>"
labels: migration
---

<!--
One issue per script. Tick each item and link its evidence (pull request, CI run).
Never paste secrets, passwords or raw audit reports here.
Guide: docs/adding-a-script.md. Rules: docs/best-practices.md.
-->

## The job

- **Script and where it runs today:**
- **What it does, in one paragraph:**
- **Owner and second contact:**

## 1. Clean it (before touching Git)

- [ ] Still needed (not one to retire)
- [ ] Staging copy shows 0 blockers in `uv run team-legacy-audit <folder>`
- [ ] `gitleaks dir <folder> -c .gitleaks.toml` reports no leaks; secrets outside the folder (task arguments, `.bat` wrappers, `cmdkey`) listed too

## 2. Bring it in (pull request: #)

- [ ] Project created with `uv run team-new-project`; libraries added with `uv add --package`
- [ ] Secrets read with `get_secret`; paths are arguments or settings
- [ ] Wrapped in `run_job`; `print` replaced by logging; no `except: pass`

## 3. Production readiness

- [ ] Owner and a second contact named in the project README and `.github/CODEOWNERS`
- [ ] On `main`, merged by pull request with CI green on Windows and Linux
- [ ] Legacy audit showed 0 blockers; gitleaks with the team config is clean
- [ ] Secrets read with `get_secret`, and changed after leaving the old script
- [ ] Wrapped in `run_job`; inputs and outputs are arguments or settings
- [ ] At least one test for its logic, using fake data
- [ ] Output compared with the old script's on the same input
- [ ] Runs under a dedicated service account, not a person
- [ ] Deployed with `deploy.ps1`; task registered with `register_task.ps1`; first run started by hand and `LastTaskResult` was 0
- [ ] Someone checks for failures: the task's history or `logs/`, until alerting exists
- [ ] Output location, who can read it, and how long it is kept are written down
- [ ] The old scheduled task is disabled only after the new one has run cleanly
