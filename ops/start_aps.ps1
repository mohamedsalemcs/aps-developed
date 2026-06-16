# ==========================================================================
# APS zero-touch launcher - brings MariaDB + Django up, idempotently.
# Safe to run any number of times: it never spawns a duplicate server.
# Runs at logon via the Startup-folder VBS (APS_AutoStart.vbs); also
# double-clickable via start_aps.bat. Logs to D:\APS_final\start_aps.log.
# (ASCII-only on purpose: Windows PowerShell 5.1 mis-decodes non-ASCII.)
# Canonical location: D:\APS_final\aps_backend\ops\  (tracked in git).
# ==========================================================================
$ErrorActionPreference = "Continue"

# Force UTF-8 for the Django child process so non-ASCII (Arabic) output never
# crashes — e.g. the console email backend printing a reset code email.
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

# Load local secrets (SMTP creds for reset emails) if present — git-ignored,
# so credentials never land in source control.
$SECRETS = "D:\APS_final\aps_backend\ops\secrets.local.ps1"
if (Test-Path $SECRETS) { . $SECRETS }

$MARIADBD = "D:\APS_final\mariadb_extract\mariadb-11.4.5-winx64\bin\mariadbd.exe"
$DATADIR  = "D:\APS_final\mariadb_data"
$PROJECT  = "D:\APS_final\aps_backend"
$VENVPY   = "D:\APS_final\aps_backend\venv\Scripts\python.exe"
$LOG      = "D:\APS_final\start_aps.log"

function Log($msg) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Add-Content -Path $LOG -Value $line -Encoding utf8
}

function Test-Port($port) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect("127.0.0.1", $port); $c.Close(); return $true
    } catch { return $false }
}

function Get-DjangoProc {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "manage\.py runserver" }
}

Log "=== start_aps run ==="

# ---- 1. MariaDB ---------------------------------------------------------
$dbWasDown = -not (Test-Port 3306)
if ($dbWasDown) {
    Log "DB down -> starting mariadbd"
    Start-Process -FilePath $MARIADBD `
        -ArgumentList "--datadir=$DATADIR", "--port=3306", "--bind-address=127.0.0.1" `
        -WindowStyle Hidden `
        -RedirectStandardOutput "D:\APS_final\mariadb_out.log" `
        -RedirectStandardError  "D:\APS_final\mariadb_err.log"
    $deadline = (Get-Date).AddSeconds(30)
    while (-not (Test-Port 3306)) {
        if ((Get-Date) -gt $deadline) { Log "ERROR: 3306 did not open within 30s - aborting"; exit 1 }
        Start-Sleep -Milliseconds 700
    }
    Log "DB up on 3306"
} else {
    Log "DB already up on 3306"
}

# ---- 2. Stale-server guard ---------------------------------------------
# Catch the orphaned/duplicate dev-server state that has misled verification:
#  - more than one logical server (a "root" = a runserver proc whose parent is
#    NOT itself a runserver; the venv shim is the root, its child is not), or
#  - a non-Django process holding :8000, or
#  - runserver procs alive but nothing listening on :8000.
# If stale: kill ALL runserver procs + whatever owns :8000, wait for the port
# to free, then fall through to a fresh start.
$djAll  = @(Get-DjangoProc)
$djPIDs = @($djAll | ForEach-Object { $_.ProcessId })
$roots  = @($djAll | Where-Object { $djPIDs -notcontains $_.ParentProcessId })
$listeners = @(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { $_.OwningProcess } | Select-Object -Unique)

$stale = $false
if ($listeners.Count -gt 0 -and @($listeners | Where-Object { $djPIDs -notcontains $_ }).Count -gt 0) { $stale = $true }
if ($roots.Count -gt 1) { $stale = $true }
if ($djPIDs.Count -gt 0 -and $listeners.Count -eq 0) { $stale = $true }

if ($stale) {
    Log "STALE state (servers=$($roots.Count) listeners=[$($listeners -join ',')] runserverPIDs=[$($djPIDs -join ',')]) -> killing all + resetting"
    @($djPIDs + $listeners) | Select-Object -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    $free = (Get-Date).AddSeconds(15)
    while (Test-Port 8000) { if ((Get-Date) -gt $free) { Log "WARN: 8000 still bound after kill"; break }; Start-Sleep -Milliseconds 500 }
    $dj = $null
} else {
    $dj = if ($djAll.Count) { $djAll[0] } else { $null }
}

# ---- 4. Resilience: if the DB had been down, restart an existing dev server
# (its DB connections may be dead) now that the DB is back.
if ($dj -and $dbWasDown) {
    Log "DB was down but Django was running -> restarting Django (PID $($dj.ProcessId))"
    $djAll | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
    $dj = $null
}

if (-not $dj) {
    Log "starting Django on 0.0.0.0:8000"
    Start-Process -FilePath $VENVPY `
        -ArgumentList "manage.py", "runserver", "0.0.0.0:8000", "--noreload" `
        -WorkingDirectory $PROJECT -WindowStyle Hidden `
        -RedirectStandardOutput "$PROJECT\server.out" `
        -RedirectStandardError  "$PROJECT\server.log"
    $deadline = (Get-Date).AddSeconds(20)
    while (-not (Test-Port 8000)) {
        if ((Get-Date) -gt $deadline) { Log "WARN: 8000 not open within 20s"; break }
        Start-Sleep -Milliseconds 700
    }
    if (Test-Port 8000) { Log "Django up on 8000" }
} else {
    Log "Django already running (PID $($dj.ProcessId)) - left as-is"
}

Log "=== done ==="
