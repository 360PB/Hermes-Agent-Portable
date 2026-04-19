@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d %~dp0
set PYTHONPATH=%CD%\hermes-agent;%CD%\venv\Lib\site-packages

echo [Hermes] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [Hermes] Environment ready. Available commands:
echo   hermes chat          - Start chat mode
echo   hermes model         - Select model
echo   hermes gateway run   - Start gateway
echo   hermes --help        - Show all commands
echo.
cmd /k
