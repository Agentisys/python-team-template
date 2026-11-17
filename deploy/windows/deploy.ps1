<#
.SYNOPSIS
    Update this server to the latest main and install exactly what uv.lock says.
.DESCRIPTION
    Refuses to deploy unless the checkout is on main with no local changes or stray
    files, then fast-forwards to origin/main and runs
    `uv sync --locked --no-dev --all-packages`, which installs team_utils and every project
    in projects/ exactly as uv.lock says.
    Stops at the first failing command. Works in Windows PowerShell 5.1 and PowerShell 7.

    Servers that read secrets from Azure Key Vault need -KeyVault on every deploy:
    uv sync removes anything not asked for, including the optional Azure libraries.
.EXAMPLE
    .\deploy\windows\deploy.ps1
.EXAMPLE
    .\deploy\windows\deploy.ps1 -KeyVault     # server uses Azure Key Vault
#>
[CmdletBinding()]
param(
    [string]$RepoPath = (Resolve-Path "$PSScriptRoot\..\..").Path,
    [switch]$KeyVault
)
$ErrorActionPreference = "Stop"

# PowerShell does not stop on a failing native command (git, uv) by itself, so every
# call goes through this: run it, then throw if its exit code is not 0.
function Invoke-Native {
    param(
        [Parameter(Mandatory)] [string]$Hint,
        [Parameter(Mandatory)] [scriptblock]$Command
    )
    # git writes progress to stderr. Under Windows PowerShell 5.1 some hosts (ISE,
    # remoting, Task Scheduler) turn stderr lines into errors, which "Stop" would treat
    # as failures. Judge success by the exit code alone.
    $ErrorActionPreference = "Continue"
    $output = & $Command
    if ($LASTEXITCODE -ne 0) { throw "$Hint (exit code $LASTEXITCODE)" }
    $output
}

foreach ($tool in "git", "uv") {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "$tool is not on PATH for $env:USERNAME. Install it machine-wide (docs/adding-a-script.md, step 8)."
    }
}

Push-Location $RepoPath
try {
    $branch = Invoke-Native "Not a git checkout: $RepoPath" { git rev-parse --abbrev-ref HEAD }
    if ($branch -ne "main") {
        throw "Servers deploy main only; this checkout is on '$branch'."
    }

    # Gitignored files (logs, output, .venv) are fine. Anything else means someone
    # edited or dropped files on the server, and pulling over it would hide that.
    $dirty = Invoke-Native "git status failed" { git status --porcelain }
    if ($dirty) {
        throw "Local changes on the server; servers must stay clean:`n$($dirty -join "`n")"
    }

    $before = Invoke-Native "git rev-parse failed" { git rev-parse --short HEAD }
    Invoke-Native "git fetch failed; check network and the deploy key" { git fetch --prune origin } | Out-Null
    Invoke-Native "git pull failed; main has diverged from origin/main" { git pull --ff-only origin main } | Out-Null
    $syncArgs = @("sync", "--locked", "--no-dev", "--all-packages")
    if ($KeyVault) { $syncArgs += @("--extra", "keyvault") }
    Invoke-Native "uv sync failed; is uv.lock in step with pyproject.toml?" { uv @syncArgs } | Out-Null
    $after = Invoke-Native "git rev-parse failed" { git rev-parse --short HEAD }

    if ($before -eq $after) {
        Write-Host "Already up to date at $after in $RepoPath"
    } else {
        Write-Host "Deployed $before -> $after in $RepoPath"
    }
}
finally {
    Pop-Location
}
