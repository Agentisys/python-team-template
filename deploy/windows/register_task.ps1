<#
.SYNOPSIS
    Register a Windows Task Scheduler job that runs a repo script through uv.
.DESCRIPTION
    The task runs under a dedicated service account (a gMSA ending in '$' is best:
    no password to store). Once the team uses Azure Key Vault (optional), that same
    account is the identity that reads it, through the server's managed identity.

    uv must be reachable by the service account. Install it to a shared folder and
    set machine-level UV_CACHE_DIR and UV_PYTHON_INSTALL_DIR so the account does not
    need its own profile copy, e.g. C:\Tools\uv, C:\uv\cache, C:\uv\python.

    Run from an elevated PowerShell. Re-running with the same -TaskName replaces the task.
.EXAMPLE
    # A job that belongs to a project in projects/: name the project with -Package.
    .\deploy\windows\register_task.ps1 -TaskName "Example - low stock" -Package example-project `
        -Script "projects\example-project\jobs\low_stock.py" -At "05:30" `
        -ServiceAccount "DOMAIN\svc-pyjobs$"
.EXAMPLE
    # Extra arguments for the script are passed through as one string:
    .\deploy\windows\register_task.ps1 -TaskName "Example - low stock" -Package example-project `
        -Script "projects\example-project\jobs\low_stock.py" `
        -ScriptArguments '--input "D:\data\stock.csv" --output "D:\data\low_stock.csv"' `
        -ServiceAccount "DOMAIN\svc-pyjobs$"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$TaskName,
    # Path relative to the repo root, e.g. projects\example-project\jobs\low_stock.py
    [Parameter(Mandatory)] [string]$Script,
    [Parameter(Mandatory)] [string]$ServiceAccount,
    [string]$ScriptArguments = "",
    # The project in projects/ the script belongs to (its pyproject name), e.g. example-project.
    [string]$Package = "",
    [string]$At = "06:00",
    [string]$TaskPath = "\PythonJobs\",
    [string]$RepoPath = (Resolve-Path "$PSScriptRoot\..\..").Path,
    [string]$UvPath
)
$ErrorActionPreference = "Stop"

# Task Scheduler stores each task as a file, so file-name characters are not allowed.
if ($TaskName -match '[\\/:*?"<>|]') {
    throw "TaskName '$TaskName' contains one of \ / : * ? `" < > |. Use e.g. 'Finance - reconcile bank'."
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "Run this from an elevated (Run as administrator) PowerShell." }

# --- Check inputs before touching Task Scheduler -------------------------------------
$scriptFull = Join-Path $RepoPath $Script
if (-not (Test-Path $scriptFull -PathType Leaf)) {
    throw "Script not found: $scriptFull (pass -Script relative to the repo root)."
}
$startAt = [datetime]::MinValue
if (-not [datetime]::TryParse($At, [ref]$startAt)) {
    throw "-At '$At' is not a time; use e.g. 06:00."
}

if (-not $UvPath) {
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uv) { throw "uv not found on PATH; install it machine-wide or pass -UvPath." }
    $UvPath = $uv.Source
}
if (-not (Test-Path $UvPath -PathType Leaf)) { throw "uv not found at $UvPath." }
# A per-user install (C:\Users\<you>\...) is not readable by the service account.
if ($UvPath -like "$env:SystemDrive\Users\*") {
    throw "uv is installed under a user profile ($UvPath). Install it machine-wide " +
        "(e.g. C:\Tools\uv\uv.exe) and pass -UvPath."
}
foreach ($var in "UV_CACHE_DIR", "UV_PYTHON_INSTALL_DIR") {
    if (-not [Environment]::GetEnvironmentVariable($var, "Machine")) {
        Write-Warning "Machine-level $var is not set; the service account will use its own profile (docs/adding-a-script.md, step 8)."
    }
}

# --- Build the task --------------------------------------------------------------------
# Quote the script path so folders with spaces work; ScriptArguments go through as given.
$uvArguments = "run --frozen --no-dev"
if ($Package) { $uvArguments += " --package $Package" }
$uvArguments += " `"$Script`""
if ($ScriptArguments) { $uvArguments += " $ScriptArguments" }

$action = New-ScheduledTaskAction -Execute $UvPath -Argument $uvArguments -WorkingDirectory $RepoPath
$trigger = New-ScheduledTaskTrigger -Daily -At $startAt
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew

$common = @{
    TaskName = $TaskName
    TaskPath = $TaskPath
    Action   = $action
    Trigger  = $trigger
    Settings = $settings
    Force    = $true
}

if ($ServiceAccount.EndsWith('$')) {
    # Group managed service account: Windows manages the password. LogonType Password
    # is how Task Scheduler expects a gMSA ("run whether user is logged on or not").
    $principal = New-ScheduledTaskPrincipal -UserId $ServiceAccount -LogonType Password
    Register-ScheduledTask @common -Principal $principal | Out-Null
} else {
    Write-Warning "$ServiceAccount is a regular account: its password is stored in Task Scheduler. Prefer a gMSA."
    $cred = Get-Credential -UserName $ServiceAccount -Message "Password for $ServiceAccount"
    Register-ScheduledTask @common -User $cred.UserName `
        -Password $cred.GetNetworkCredential().Password | Out-Null
}

Write-Host "Registered '$TaskPath$TaskName' daily at $($startAt.ToString('HH:mm')) as $ServiceAccount"
Write-Host "  $UvPath $uvArguments"
Write-Host "  in $RepoPath"
Write-Host "Test it now:  Start-ScheduledTask -TaskPath '$TaskPath' -TaskName '$TaskName'"
Write-Host "Then check:   Get-ScheduledTaskInfo -TaskPath '$TaskPath' -TaskName '$TaskName'  (LastTaskResult 0 = success)"
