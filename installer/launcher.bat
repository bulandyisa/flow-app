@echo off
chcp 65001 >nul 2>&1
title Flow App

set "APP_ROOT=%~dp0"
if "%APP_ROOT:~-1%"=="\" set "APP_ROOT=%APP_ROOT:~0,-1%"

set "NODE_EXE=%APP_ROOT%\node\node.exe"
set "APP_DIR=%APP_ROOT%\app"
set "DATA_DIR=%APP_ROOT%\data"

:: Check Node.js exists
if not exist "%NODE_EXE%" (
    echo [ERROR] Node.js not found: %NODE_EXE%
    echo Please reinstall the application.
    pause
    exit /b 1
)

:: Check app code exists
if not exist "%APP_DIR%\packages\server\dist\index.js" (
    echo [ERROR] Application code not found.
    echo Please reinstall the application.
    pause
    exit /b 1
)

:: Create data dirs
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"
if not exist "%DATA_DIR%\projects" mkdir "%DATA_DIR%\projects"
if not exist "%DATA_DIR%\sessions" mkdir "%DATA_DIR%\sessions"

:: ============================================
:: Check for updates
:: ============================================
echo.
echo  Flow App - starting...
echo.

"%NODE_EXE%" "%APP_ROOT%\update-checker.js" "%APP_ROOT%"

:: ============================================
:: Find a free port (3000, 3001, 3002...)
:: ============================================
set "PORT=3000"

:find_port
"%NODE_EXE%" -e "const s=require('net').createServer();s.listen(%PORT%,()=>{s.close();process.exit(0)});s.on('error',()=>process.exit(1))" >nul 2>&1
if %errorlevel% equ 0 goto port_found
set /a PORT+=1
if %PORT% gtr 3010 (
    echo [ERROR] No free port found (3000-3010).
    pause
    exit /b 1
)
goto find_port

:port_found

:: ============================================
:: Start server
:: ============================================
set "NODE_ENV=production"
set "DATA_DIR=%APP_ROOT%\data"
set "PYTHON_PATH=%APP_ROOT%\python\python.exe"
set "FFMPEG_DIR=%APP_ROOT%\ffmpeg"
set "PLAYWRIGHT_BROWSERS_PATH=%APP_ROOT%\chromium"
set "APP_ROOT_DIR=%APP_ROOT%"

echo  Starting server on port %PORT%...

:: Start server in background, save PID
start /b "" "%NODE_EXE%" "%APP_DIR%\packages\server\dist\index.js"

:: Wait for server to be ready
set RETRIES=0

:wait_server
timeout /t 1 /nobreak >nul
set /a RETRIES+=1

"%NODE_EXE%" -e "fetch('http://localhost:%PORT%/api/auth/status').then(r=>{process.exit(r.ok?0:1)}).catch(()=>process.exit(1))" >nul 2>&1
if %errorlevel% equ 0 goto server_ready

if %RETRIES% lss 15 goto wait_server

echo [ERROR] Server did not start within 15 seconds.
:: Kill any node process we may have started
taskkill /f /im node.exe /fi "WINDOWTITLE eq Flow App" >nul 2>&1
pause
exit /b 1

:server_ready
echo.
echo  Flow App: http://localhost:%PORT%
echo.

start http://localhost:%PORT%

:: ============================================
:: Wait until window is closed, then kill server
:: ============================================
:keep_alive
timeout /t 5 /nobreak >nul

:: Check if node is still running (server alive)
"%NODE_EXE%" -e "fetch('http://localhost:%PORT%/api/auth/status').then(()=>process.exit(0)).catch(()=>process.exit(1))" >nul 2>&1
if %errorlevel% equ 0 goto keep_alive

:: Server died on its own, exit
exit /b 0
