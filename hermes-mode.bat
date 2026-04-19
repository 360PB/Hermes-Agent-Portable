@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d %~dp0
set PYTHONPATH=%CD%\hermes-agent;%CD%\venv\Lib\site-packages
"%CD%\python_runtime\python.exe" -m hermes_cli.main model"
pause