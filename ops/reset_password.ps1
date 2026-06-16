# ==========================================================================
# APS CMS — forgot-password recovery (run on the server).
# Resets the admin password. Pass a new password, or run with no argument to
# auto-generate a strong one (it gets printed). Then log in with it.
#   ops\reset_password.ps1 "MyNewPassword"
#   ops\reset_password.ps1                 (auto-generates)
# ==========================================================================
param([string]$Password = "")

$ErrorActionPreference = "Stop"
$PY = "D:\APS_final\aps_backend\venv\Scripts\python.exe"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
Set-Location "D:\APS_final\aps_backend"

if ($Password) {
    & $PY manage.py setadminpw $Password --user aps_admin
} else {
    & $PY manage.py setadminpw --user aps_admin
}
