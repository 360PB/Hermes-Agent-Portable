@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d %~dp0

set PYTHONPATH=%CD%\venv\Lib\site-packages
set HERMES_WEBUI_AGENT_DIR=%CD%\hermes-agent
set HERMES_WEBUI_PYTHON=%CD%\python_runtime\python.exe

echo Starting Hermes WebUI...
start "Hermes WebUI" "%CD%\python_runtime\python.exe" "%CD%\hermes-webui\server.py"

echo Waiting for server...
ping 127.0.0.1 -n 4 >nul

echo Opening browser...
start http://127.0.0.1:8787