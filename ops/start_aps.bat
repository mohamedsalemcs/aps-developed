@echo off
REM Double-click safety net - brings MariaDB + Django up (idempotent).
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0start_aps.ps1"
