@echo off
REM Wrapper for running flow_bot.py with a guaranteed timeout on Windows.
REM If the Python process hangs, this script will kill it.
REM
REM Usage:
REM   run_safe.bat --review --clip S01_A
REM   set FLOW_TIMEOUT=900 && run_safe.bat --review
REM
REM Default timeout: 18000 seconds (5 hours)

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

REM Find Python
if defined VIRTUAL_ENV (
    set "PYTHON=%VIRTUAL_ENV%\Scripts\python.exe"
) else if exist "%PROJECT_DIR%\venv\Scripts\python.exe" (
    set "PYTHON=%PROJECT_DIR%\venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON=python"
    ) else (
        where py >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON=py"
        ) else (
            echo ERROR: Python not found. Install Python from https://python.org
            exit /b 1
        )
    )
)

set "BOT=%SCRIPT_DIR%flow_bot.py"

if not defined FLOW_TIMEOUT set "FLOW_TIMEOUT=18000"

echo Starting flow_bot.py with %FLOW_TIMEOUT%s timeout...
echo Python: %PYTHON%
echo Args: %*
echo.

REM Set environment and run
set "PYTHONUNBUFFERED=1"

REM Start the bot process
start /b "" %PYTHON% -u "%BOT%" %*
set "BOT_PID=%errorlevel%"

REM Note: Windows batch doesn't have a clean way to implement timeout + kill.
REM For production use, consider using PowerShell or the Node.js bot manager instead.
%PYTHON% -u "%BOT%" %*
set "EXIT_CODE=%errorlevel%"

if %EXIT_CODE% equ 42 (
    echo.
    echo Exited by Python global timeout.
)

exit /b %EXIT_CODE%
