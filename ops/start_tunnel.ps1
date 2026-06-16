# ==========================================================================
# APS Cloudflare quick-tunnel launcher - exposes the local site/CMS over HTTPS.
# Idempotent: if a tunnel is already running it just reports the saved URL.
# 1) ensure the site is up (calls start_aps.ps1), 2) start cloudflared,
# 3) extract the https://*.trycloudflare.com URL, 4) save it to tunnel_url.txt.
# ASCII-only (Windows PowerShell 5.1 mis-decodes non-ASCII).
# ==========================================================================
$ErrorActionPreference = "Continue"

$CF       = "cloudflared"
$STARTAPS = "D:\APS_final\aps_backend\ops\start_aps.ps1"
$URLFILE  = "D:\APS_final\tunnel_url.txt"
$OUTLOG   = "D:\APS_final\tunnel_out.log"
$ERRLOG   = "D:\APS_final\tunnel_err.log"
$LOG      = "D:\APS_final\tunnel.log"
$RX       = "https://[a-z0-9-]+\.trycloudflare\.com"

function Log($msg) {
    Add-Content -Path $LOG -Value ("{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg) -Encoding utf8
}

Log "=== start_tunnel run ==="

# ---- 1. ensure the local site is up -------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File $STARTAPS | Out-Null

# ---- 2. already running? report the saved URL ---------------------------
$existing = Get-Process cloudflared -ErrorAction SilentlyContinue
if ($existing -and (Test-Path $URLFILE)) {
    $u = (Get-Content $URLFILE -Raw).Trim()
    Log "cloudflared already running -> $u"
    Write-Output "Tunnel already running:"
    Write-Output "  $u"
    exit 0
}
if ($existing) {
    # running but no saved URL - restart cleanly so we can recapture it
    Log "cloudflared running without saved URL -> restarting"
    $existing | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# ---- 3. start the tunnel + capture its URL ------------------------------
Remove-Item $OUTLOG, $ERRLOG -Force -ErrorAction SilentlyContinue
Start-Process -FilePath $CF `
    -ArgumentList "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:8000" `
    -WindowStyle Hidden -RedirectStandardOutput $OUTLOG -RedirectStandardError $ERRLOG

$url = $null
$deadline = (Get-Date).AddSeconds(45)
while (-not $url -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 800
    foreach ($f in @($ERRLOG, $OUTLOG)) {
        if (Test-Path $f) {
            $m = Select-String -Path $f -Pattern $RX -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($m) { $url = $m.Matches[0].Value; break }
        }
    }
}

if (-not $url) {
    Log "ERROR: no trycloudflare URL captured within 45s"
    Write-Output "FAILED: could not capture tunnel URL (see $ERRLOG)"
    exit 1
}

# ---- 4. save + announce -------------------------------------------------
Set-Content -Path $URLFILE -Value $url -Encoding ascii
Log "tunnel up -> $url"
Write-Output ""
Write-Output "=================================================================="
Write-Output "  PUBLIC URL : $url"
Write-Output "  Site       : $url/"
Write-Output "  Arabic     : $url/ar/"
Write-Output "  CMS login  : $url/cms/login/   (user: aps_admin)"
Write-Output "  saved to   : $URLFILE"
Write-Output "=================================================================="
