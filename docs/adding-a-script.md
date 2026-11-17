# Adding an existing script

How to move a script that runs on a server today into this repository, and back onto
the server as a scheduled job deployed from `main`. Open a **Migrate a script** issue
first: it carries this checklist so nothing gets skipped.

Everything committed stays in Git history and in every clone. Removing a secret later
takes a history rewrite *and* a password change, so clean first.

## Ground rules

- **Never `git init` inside an existing script folder.** Work on a copy. The original
  keeps running until the new job has run cleanly.
- **Never bring old history over.** If the folder has `.git` or `.svn`, leave it behind.
- **Every secret you find is compromised.** It sat in plain text on a shared server, so
  change it with the system's owner once the job reads it the new way.
- **Reports are sensitive.** Audit and scan reports name servers and sometimes
  passwords. Keep them out of the repo, Teams and email, and delete them afterwards.

## 1. Copy the folder without the junk

```powershell
$src = "C:\scripts\finance"             # or \\server1\c$\scripts\finance
$dst = "C:\staging\finance"
robocopy $src $dst /E `
    /XD .git .svn .hg venv .venv env __pycache__ site-packages .idea logs output `
    /XF *.pyc *.pyo *.log *.bak *.tmp
if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE)" }   # 0-7 mean success
```

Also check where secrets hide *outside* the folder: the scheduled task's arguments,
`.bat` wrappers (`net use ... /user:`), machine environment variables, and
`cmdkey /list` as the task's account.

## 2. Audit the copy

From the repo root:

```powershell
New-Item -ItemType Directory -Force C:\staging-reports | Out-Null   # outside the repo
uv run team-legacy-audit C:\staging\finance > C:\staging-reports\finance-audit.txt
gitleaks dir C:\staging\finance -c .gitleaks.toml --redact -v
```

| Audit level | Means | Fix |
| --- | --- | --- |
| BLOCKER | Must not be committed: old venvs, `.git`, credential files, data exports, files over 500 KB | Delete it from the copy |
| JUNK | Safe to delete: `__pycache__`, `*.bak`, Office lock files | Delete it |
| REVIEW | Hard-coded paths, IP addresses, server names | Make it a setting in `.env.example` or an `--input` / `--output` argument |
| INFO | Not UTF-8, Python 2, and the packages each script imports | Convert; the import list is your `uv add` list |

**Use `-c .gitleaks.toml`.** Without it gitleaks misses plain passwords in connection
strings and `.ini` files. Repeat until the audit shows 0 blockers and gitleaks finds
nothing.

## 3. Create the project

```bash
git switch main
git pull
git switch -c feat/migrate-finance-recon
uv run team-new-project finance-recon --description "Nightly bank reconciliation."
uv lock
uv sync --all-packages
```

Then add the libraries it imports, at the versions that work on the server today:

```bash
uv add --package finance-recon "requests==2.31.0" "openpyxl==3.1.2"
```

## 4. Bring the code in

| Old script did | Now it does |
| --- | --- |
| Everything in one file | Logic in `src/finance_recon/`, a thin job in `jobs/` |
| `password = "..."` | `get_secret("finance-db-password")`, value in `.env` |
| `C:\scripts\output\...` | An `--output` argument, or a setting in `.env.example` |
| `print(...)` | `logging` (`log = logging.getLogger(__name__)`) |
| Ran top to bottom | `raise SystemExit(run_job("finance-recon.reconcile", main))` at the end |
| `except: pass` | Let it fail: `run_job` logs the error and exits with code 1 |

Write at least one test for the logic in `tests/`, using small **fake** data. Run the
new job and the old script on the same input and compare the output.

## 5. Fill in the project README and CODEOWNERS

Owner, jobs, schedule, inputs, outputs, settings and secret names. Add
`/projects/finance-recon/  @your-org/your-team` to `.github/CODEOWNERS`.

## 6. Open the pull request

```bash
uv run ruff check --fix .
uv run ruff format .
uv run pytest
uv run pre-commit run --all-files
gitleaks git . --redact -v              # every commit on this branch
git push -u origin HEAD
```

CI scans every commit again, so a secret added and then deleted on the branch still
fails the pull request.

## 7. Change the secrets

Each secret the old script held: change it with the owning system, and put the new value
only in the server's `.env` (or Key Vault, once the team has one).

## 8. Deploy and schedule

**One-time server setup** (an admin, in an elevated PowerShell):

1. Install Git and uv **machine-wide**, so the service account can use them:

   ```powershell
   winget install --id Git.Git -e --scope machine
   $env:UV_INSTALL_DIR = "C:\Tools\uv"
   powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
   $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
   [Environment]::SetEnvironmentVariable("Path", "$machinePath;C:\Tools\uv", "Machine")
   [Environment]::SetEnvironmentVariable("UV_CACHE_DIR", "C:\uv\cache", "Machine")
   [Environment]::SetEnvironmentVariable("UV_PYTHON_INSTALL_DIR", "C:\uv\python", "Machine")
   ```

   Open a new PowerShell afterwards so the new PATH applies.
2. **Give the server read-only access to the repository** with a deploy key:

   ```powershell
   ssh-keygen -t ed25519 -f "$HOME\.ssh\deploy_key" -C "server1 deploy key"
   Get-Content "$HOME\.ssh\deploy_key.pub"     # copy this line
   ```

   Press Enter twice at the passphrase prompts: the scheduled deploy can't type one.

   On GitHub: the repository's *Settings → Deploy keys → Add deploy key*, paste the
   line, leave **Allow write access** unticked. Then clone over SSH with that key:

   ```powershell
   git -c core.sshCommand="ssh -i $HOME/.ssh/deploy_key" clone git@github.com:your-org/your-repo.git C:\repos\your-repo
   cd C:\repos\your-repo
   git config core.sshCommand "ssh -i $HOME/.ssh/deploy_key"
   ```

   Deploy as this same admin account, which holds the key.
3. **Create a service account** for jobs (a gMSA if your domain supports it). Give it read
   access to the repository folder, and write access to `logs\` and the uv folders:

   ```powershell
   New-Item -ItemType Directory -Force C:\repos\your-repo\logs, C:\uv\cache, C:\uv\python | Out-Null
   icacls C:\repos\your-repo /grant 'DOMAIN\svc-pyjobs$:(OI)(CI)RX'
   icacls C:\repos\your-repo\logs /grant 'DOMAIN\svc-pyjobs$:(OI)(CI)M'
   icacls C:\uv /grant 'DOMAIN\svc-pyjobs$:(OI)(CI)M'
   ```

4. **Create the server's `.env`** in the repository folder from `.env.example`, with the
   real values. Restrict it to the service account and administrators (`*S-1-5-32-544`
   is the local Administrators group in any language):

   ```powershell
   cd C:\repos\your-repo
   Copy-Item .env.example .env        # then fill in the values
   icacls .env /inheritance:r /grant:r 'DOMAIN\svc-pyjobs$:R' '*S-1-5-32-544:F'
   ```

**Every deploy**, after the pull request merges:

```powershell
.\deploy\windows\deploy.ps1            # add -KeyVault once the server uses Azure Key Vault
```

It refuses to run if anyone edited files on the server, then pulls `main` and installs
exactly what `uv.lock` says.

**Schedule the job** (once per job, from an elevated PowerShell):

```powershell
.\deploy\windows\register_task.ps1 -TaskName "Finance - reconcile bank" -Package finance-recon `
    -Script "projects\finance-recon\jobs\reconcile_bank.py" -At "02:00" `
    -ServiceAccount "DOMAIN\svc-pyjobs$"
```

Start it by hand once and check `LastTaskResult` is 0 and the log in `logs\` looks right.
Disable the old task only after the new one has run cleanly; delete it after an agreed
period.
