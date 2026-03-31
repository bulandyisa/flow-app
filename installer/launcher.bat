@echo off
chcp 65001 >nul 2>&1
title Flow App

:: ============================================
:: 1. Set environment variables
:: ============================================
set "APP_ROOT=%~dp0"
if "%APP_ROOT:~-1%"=="\" set "APP_ROOT=%APP_ROOT:~0,-1%"

set "NODE_EXE=%APP_ROOT%\node\node.exe"
set "APP_DIR=%APP_ROOT%\app"
set "DATA_DIR=%APP_ROOT%\data"

set "NODE_ENV=production"
set "PYTHON_PATH=%APP_ROOT%\python\python.exe"
set "FFMPEG_DIR=%APP_ROOT%\ffmpeg"
set "PLAYWRIGHT_BROWSERS_PATH=%APP_ROOT%\chromium"
set "APP_ROOT_DIR=%APP_ROOT%"

echo.
echo  ========================================
echo   Flow App - Launcher
echo  ========================================
echo.

:: ============================================
:: 2. Check node.exe exists
:: ============================================
echo  [1/7] Checking Node.js...
if not exist "%NODE_EXE%" (
    echo  [ERROR] Node.js not found: %NODE_EXE%
    echo  Please reinstall the application.
    pause
    exit /b 1
)
echo  OK: Node.js found

:: ============================================
:: 3. Check app code exists
:: ============================================
echo  [2/7] Checking application code...
if not exist "%APP_DIR%\packages\server\dist\index.js" (
    echo  [ERROR] Application code not found.
    echo  Please reinstall the application.
    pause
    exit /b 1
)
echo  OK: Application code found

:: ============================================
:: 4. Create data directories
:: ============================================
echo  [3/7] Checking data directories...
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"
if not exist "%DATA_DIR%\projects" mkdir "%DATA_DIR%\projects"
if not exist "%DATA_DIR%\sessions" mkdir "%DATA_DIR%\sessions"
echo  OK: Data directories ready

:: ============================================
:: 5. Kill previous FlowApp node processes
:: ============================================
echo  [4/7] Checking for previous instances...
tasklist /fi "IMAGENAME eq node.exe" /fo csv 2>nul | findstr /i "node" >nul
if %errorlevel% equ 0 (
    echo  Stopping previous node.exe processes...
    taskkill /f /im node.exe >nul 2>&1
    timeout /t 2 /nobreak >nul
    echo  OK: Previous processes stopped
) else (
    echo  OK: No previous instances found
)

:: ============================================
:: 6. Run update checker (if exists)
:: ============================================
echo  [5/7] Checking for updates...
if exist "%APP_ROOT%\update-checker.js" (
    "%NODE_EXE%" "%APP_ROOT%\update-checker.js" "%APP_ROOT%"
    echo  OK: Update check complete
) else (
    echo  Skipped: No update checker found
)

:: ============================================
:: 7. Find a free port
:: ============================================
echo  [6/7] Finding free port...
set "PORT=3000"

:: Write port finder script to temp file (each echo is outside block to avoid double-parsing)
set "PF=%TEMP%\_fa_port.js"
echo var net = require('net'); > "%PF%"
echo var port = parseInt(process.argv[2] ^|^| '3000');>> "%PF%"
echo var s = net.createServer();>> "%PF%"
echo s.listen(port, function() { s.close(); process.exit(0); });>> "%PF%"
echo s.on('error', function() { process.exit(1); });>> "%PF%"

:find_port
"%NODE_EXE%" "%PF%" %PORT% >nul 2>&1
if %errorlevel% equ 0 goto port_found
set /a PORT+=1
if %PORT% gtr 3020 (
    echo  [ERROR] No free port found in range 3000-3020.
    del "%PF%" >nul 2>&1
    pause
    exit /b 1
)
goto find_port

:port_found
del "%PF%" >nul 2>&1
echo  OK: Port %PORT% is free

:: ============================================
:: 8. Write server health check script (once, reused for startup + keep-alive)
:: ============================================
set "HC=%TEMP%\_fa_check.js"
echo var http = require('http'); > "%HC%"
echo var port = process.argv[2] ^|^| '3000';>> "%HC%"
echo var req = http.get('http://localhost:' + port + '/api/auth/status', function(res) {>> "%HC%"
echo   process.exit(res.statusCode ^>= 200 ^&^& res.statusCode ^< 400 ? 0 : 1);>> "%HC%"
echo });>> "%HC%"
echo req.on('error', function() { process.exit(1); });>> "%HC%"
echo req.setTimeout(3000, function() { req.destroy(); process.exit(1); });>> "%HC%"

:: ============================================
:: 9. Start server
:: ============================================
echo  [7/7] Starting server on port %PORT%...
echo.

start /b "" "%NODE_EXE%" "%APP_DIR%\packages\server\dist\index.js"

:: ============================================
:: 10. Wait for server to be ready (up to 30 seconds)
:: ============================================
set RETRIES=0

:wait_server
timeout /t 1 /nobreak >nul
set /a RETRIES+=1
echo  Waiting for server... (%RETRIES%/30)

"%NODE_EXE%" "%HC%" %PORT% >nul 2>&1
if %errorlevel% equ 0 goto server_ready

if %RETRIES% lss 30 goto wait_server

echo.
echo  [ERROR] Server did not start within 30 seconds.
echo  Check the logs above for errors.
del "%HC%" >nul 2>&1
pause
exit /b 1

:server_ready
echo.
echo  ========================================
echo   Flow App is running!
echo   http://localhost:%PORT%
echo  ========================================
echo.
echo  Opening browser...

start http://localhost:%PORT%

echo.
echo  Server is running. Close this window to stop.
echo.

:: ============================================
:: 11. Keep alive until server stops
:: ============================================
:keep_alive
timeout /t 5 /nobreak >nul

"%NODE_EXE%" "%HC%" %PORT% >nul 2>&1
if %errorlevel% equ 0 goto keep_alive

:: Server stopped — cleanup
del "%HC%" >nul 2>&1
echo.
echo  Server stopped.
exit /b 0
