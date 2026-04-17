@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
setlocal enabledelayedexpansion
cd /d %~dp0

set PATH=%CD%\tools;%PATH%
set VIRTUAL_ENV=%CD%\venv
set PYTHONPATH=%CD%\venv\Lib\site-packages

:: Check if hermes-agent is the original repo
cd /d %~dp0\hermes-agent
git remote -v 2>nul | findstr /i "hermes-agent" >nul
if %errorlevel% equ 0 (
    echo [1/4] Running hermes update...
    "%~dp0python_runtime\python.exe" -m hermes_cli.main update
    if %errorlevel% neq 0 (
        echo [ERROR] hermes update failed.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Syncing hermes-agent source from upstream NousResearch...
    set "ZIP_TMP=%TEMP%\hermes-agent-upstream-%RANDOM%.zip"
    set "EXTRACT_TMP=%TEMP%\hermes-agent-upstream-%RANDOM%"
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/nousresearch/hermes-agent/archive/refs/heads/main.zip' -OutFile '!ZIP_TMP!'" >nul 2>&1
    if !errorlevel! neq 0 (
        echo [WARN] Failed to download upstream source. Skipping source sync.
        del /f /q "!ZIP_TMP!" 2>nul
    ) else (
        powershell -Command "Expand-Archive -Path '!ZIP_TMP!' -DestinationPath '!EXTRACT_TMP!' -Force" >nul 2>&1
        if !errorlevel! neq 0 (
            echo [WARN] Failed to extract upstream source.
            del /f /q "!ZIP_TMP!" 2>nul
        ) else (
            for /f "delims=" %%d in ('dir /b /ad "!EXTRACT_TMP!\hermes-agent-*" 2^>nul') do (
                robocopy "!EXTRACT_TMP!\%%d" "%~dp0hermes-agent" /E /XD venv node_modules .git /XF .env >nul
                if !errorlevel! geq 8 (
                    echo [WARN] Source sync may have encountered issues ^(robocopy exit: !errorlevel!^).
                ) else (
                    echo ^> Source synced successfully.
                )
            )
            rd /s /q "!EXTRACT_TMP!" 2>nul
            del /f /q "!ZIP_TMP!" 2>nul
        )
    )
)

echo.
echo [2/4] Converting editable install to normal install...
cd /d %~dp0\hermes-agent
"%~dp0tools\uv.exe" pip install . --force-reinstall --no-deps
if %errorlevel% neq 0 (
    echo [WARN] Normal install failed.
    pause
    exit /b 1
)

echo.
echo [3/4] Cleaning __pycache__...
for /f "delims=" %%d in ('dir /s /b __pycache__ 2^>nul') do (
    rd /s /q "%%d" 2>nul
)

echo.
echo [4/4] Updating hermes-webui...
cd /d %~dp0\hermes-webui
git remote -v 2>nul | findstr /i "nesquena/hermes-webui" >nul
if %errorlevel% equ 0 (
    git pull
    if %errorlevel% neq 0 (
        echo [INFO] hermes-webui git pull failed.
    )
) else (
    echo ^> Syncing hermes-webui source from upstream nesquena...
    set "ZIP_TMP=%TEMP%\hermes-webui-upstream-%RANDOM%.zip"
    set "EXTRACT_TMP=%TEMP%\hermes-webui-upstream-%RANDOM%"
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/nesquena/hermes-webui/archive/refs/heads/main.zip' -OutFile '!ZIP_TMP!'" >nul 2>&1
    if !errorlevel! neq 0 (
        echo [WARN] Failed to download upstream webui source. Skipping source sync.
        del /f /q "!ZIP_TMP!" 2>nul
    ) else (
        powershell -Command "Expand-Archive -Path '!ZIP_TMP!' -DestinationPath '!EXTRACT_TMP!' -Force" >nul 2>&1
        if !errorlevel! neq 0 (
            echo [WARN] Failed to extract upstream webui source.
            del /f /q "!ZIP_TMP!" 2>nul
        ) else (
            for /f "delims=" %%d in ('dir /b /ad "!EXTRACT_TMP!\hermes-webui-*" 2^>nul') do (
                robocopy "!EXTRACT_TMP!\%%d" "%~dp0hermes-webui" /E /XD venv node_modules .git /XF .env >nul
                if !errorlevel! geq 8 (
                    echo [WARN] WebUI source sync may have encountered issues ^(robocopy exit: !errorlevel!^).
                ) else (
                    echo ^> WebUI source synced successfully.
                )
            )
            rd /s /q "!EXTRACT_TMP!" 2>nul
            del /f /q "!ZIP_TMP!" 2>nul
        )
    )
)
cd /d %~dp0

echo.
echo ========================================
echo  Update complete!
echo ========================================
pause
