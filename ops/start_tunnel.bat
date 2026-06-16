@echo off
REM Double-click to expose the APS site/CMS over a public HTTPS tunnel.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_tunnel.ps1"
