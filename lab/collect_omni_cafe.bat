@echo off
chcp 65001 >nul
cd /d "%~dp0"
REM no Python; system PowerShell only. Prefer: right-click Run as administrator
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0collect_omni_cafe.ps1"
echo.
echo Done. You can close this window.
pause