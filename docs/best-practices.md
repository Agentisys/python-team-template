# Best practices

The rules this team follows, and why. Most are enforced automatically (ruff, gitleaks,
CI, the `main` ruleset); the rest are checked in review. If one can't be met for a job,
open a **Standards exception** issue rather than quietly skipping it.

## Code

- **All code that runs on a server lives in this repo.** Nothing is edited on a server;
  `deploy.ps1` refuses a server with local changes.
- **Every change reaches `main` through a reviewed pull request with green CI.**
- **Logic in `src/`, thin jobs in `jobs/`.** Logic you can import, you can test.
- **Every job ends with `run_job`.** It logs start, finish and failures, and returns exit
  code 1 on failure so Task Scheduler sees it.
- **`logging`, not `print`,** in `src/`. Never log a secret value or personal data.
- **No silent failures.** No bare `except:` or `except Exception: pass`. Let it fail loudly.
- **Inputs and outputs are arguments or settings,** never hard-coded paths or server names.
- **Shared code goes in `src/team_utils/`** only once two or more projects need it, in its
  own pull request, with tests.
- **Fix lint findings rather than silencing them.** A `# noqa` gives its reason on the
  same line.

## Secrets

- **No secrets in code, config files, logs or Git history.** gitleaks checks every commit.
- **Read secrets only with `get_secret("kebab-case-name")`.** Today the value comes from
  `.env`; once the team uses Azure Key Vault, from there, with no code change.
- **`.env` is never committed or shared** over Teams or email. On servers it is readable
  only by the service account and admins.
- **A secret that was ever committed or shared is compromised.** Change it; deleting the
  line is not enough.
- **Move to Azure Key Vault when you can.** Secrets then live in one audited place, and
  servers read them with a managed identity instead of a file.

## Dependencies

- **Add and remove only with `uv add` / `uv remove`.** `uv.lock` pins exact, hashed
  versions; never edit it by hand, always commit it.
- **Before adding a library, check:** is it maintained, widely used, and from the
  publisher you expect (watch for look-alike names)? Is it needed, or does the standard
  library do it? Say why in the pull request.
- **Review Dependabot pull requests** weekly, like any other change.

## Running jobs

- **Jobs run as a dedicated service account,** never a person's account, with only the
  folders and access the job needs.
- **Servers run `main`, deployed with `deploy.ps1`.** Rollback is "revert the pull request,
  then deploy".
- **Jobs are safe to re-run,** or their README says what to clean up first.
- **Use TLS for every network call.** Never `verify=False`.
- **Read only the data you need,** and write down where outputs go, who can read them and
  how long they are kept.

## Readiness checklist

A job is ready for production when every box is ticked. The **Migrate a script** issue
template carries the same list.

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
