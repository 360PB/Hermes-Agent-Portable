@echo off
chcp 65001 >nul
echo ==========================================
echo   Hermes Agent Portable - Update Upstream
echo ==========================================
powershell -ExecutionPolicy Bypass -File "%~dp0update-upstream.ps1" %*
echo.
pause
