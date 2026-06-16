# ==========================================================================
# APS ngrok launcher - exposes the local site/CMS on a STABLE ngrok domain.
# Unlike the Cloudflare quick tunnel, the URL never changes and won't die on
# its own. Reads the reserved static domain from ngrok_domain.txt (one line,
# e.g. aps-cms.ngrok-free.app) or the -Domain parameter.
# 1) ensure the site is up (start_aps.ps1), 2) (re)start ngrok on the domain,
# 3) save the https URL to tunnel_url.txt (kept for backward-compat).
# ASCII-only (Windows PowerShell 5.1 mis-decodes non-ASCII).
# ==========================================================================
param([string]$Domain = "")

$ErrorActionPreference = "Continue"

$NGROK    = "ngrok"
$STARTAPS = "D:\APS_final\aps_backend\ops\start_aps.ps1"
$DOMFILE  = "D:\APS_final\ngrok_domain.txt"
$URLFILE  = "D:\APS_final\tunnel_url.txt"
$OUTLOG   = "D:\APS_final\ngrok_out.log"
$ERRLOG   = "D:\APS_final\ngrok_err.log"
$LOG      = "D:\APS_final\ngrok.log"

function Log($msg) {
    Add-Content -Path $LOG -Value ("{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg) -Encoding utf8
}

Log "=== start_ngrok run ==="

# ---- 0. resolve the reserved domain -------------------------------------
if (-not $Domain -and (Test-Path $DOMFILE)) {
    $Domain = (Get-Content $DOMFILE -Raw).Trim()
}
if (-not $Domain) {
    Write-Output "FAILED: no ngrok domain. Pass -Domain <your-domain> or put it in $DOMFILE"
    Log "ERROR: no domain"
    exit 1
}
# persist for next time
Set-Content -Path $DOMFILE -Value $Domain -Encoding ascii

# ---- 1. ensure the local site is up -------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File $STARTAPS | Out-Null

# ---- 2. restart ngrok cleanly on the fixed domain -----------------------
Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Remove-Item $OUTLOG, $ERRLOG -Force -ErrorAction SilentlyContinue

Start-Process -FilePath $NGROK `
    -ArgumentList "http", "--domain=$Domain", "--log=stdout", "--log-format=logfmt", "8000" `
    -WindowStyle Hidden -RedirectStandardOutput $OUTLOG -RedirectStandardError $ERRLOG

# ---- 3. confirm the tunnel established (poll ngrok local API) ------------
$ok = $false
$deadline = (Get-Date).AddSeconds(25)
while (-not $ok -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 800
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 3
        if ($r.tunnels | Where-Object { $_.public_url -like "https://*" }) { $ok = $true }
    } catch { }
    # surface auth/domain errors early
    if (Test-Path $ERRLOG) {
        $err = Select-String -Path $ERRLOG -Pattern "ERR_NGROK|authentication failed|not authorized|reserve" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($err) { Log ("ngrok error: " + $err.Line); break }
    }
}

$url = "https://$Domain"
if (-not $ok) {
    Write-Output "WARNING: could not confirm tunnel within 25s. Check $ERRLOG (auth token? domain reserved?)."
    Log "WARN: tunnel not confirmed"
} else {
    Log "ngrok up -> $url"
}

# ---- 4. save + announce -------------------------------------------------
Set-Content -Path $URLFILE -Value $url -Encoding ascii
Write-Output ""
Write-Output "=================================================================="
Write-Output "  STABLE URL : $url"
Write-Output "  Site       : $url/"
Write-Output "  Arabic     : $url/ar/"
Write-Output "  CMS login  : $url/cms/login/   (user: aps_admin)"
Write-Output "  Inspector  : http://127.0.0.1:4040"
Write-Output "  saved to   : $URLFILE"
Write-Output "=================================================================="
