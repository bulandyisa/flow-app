@echo off
chcp 65001 >nul 2>&1
title Flow App

:: ============================================
:: Flow App Launcher
:: Проверяет обновления, запускает сервер, открывает браузер
:: ============================================

set "APP_ROOT=%~dp0"
:: Убираем trailing backslash
if "%APP_ROOT:~-1%"=="\" set "APP_ROOT=%APP_ROOT:~0,-1%"

set "NODE_EXE=%APP_ROOT%\node\node.exe"
set "APP_DIR=%APP_ROOT%\app"
set "DATA_DIR=%APP_ROOT%\data"
set "VERSION_FILE=%APP_DIR%\version.json"

:: Проверяем что Node.js на месте
if not exist "%NODE_EXE%" (
    echo [ОШИБКА] Node.js не найден: %NODE_EXE%
    echo Переустановите приложение.
    pause
    exit /b 1
)

:: Проверяем что код приложения на месте
if not exist "%APP_DIR%\packages\server\dist\index.js" (
    echo [ОШИБКА] Код приложения не найден.
    echo Переустановите приложение.
    pause
    exit /b 1
)

:: Создаём data директорию если нет
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"
if not exist "%DATA_DIR%\projects" mkdir "%DATA_DIR%\projects"
if not exist "%DATA_DIR%\sessions" mkdir "%DATA_DIR%\sessions"

:: ============================================
:: Проверка обновлений
:: ============================================
echo.
echo  Flow App - запуск...
echo  ─────────────────────
echo.
echo  Проверяю обновления...

"%NODE_EXE%" "%APP_ROOT%\update-checker.js" "%APP_ROOT%"
set UPDATE_RESULT=%errorlevel%

if %UPDATE_RESULT% equ 2 (
    echo  Обновление установлено! Запускаю обновлённую версию...
    echo.
)
if %UPDATE_RESULT% equ 1 (
    echo  Не удалось проверить обновления, запускаю текущую версию.
    echo.
)
if %UPDATE_RESULT% equ 0 (
    echo  Версия актуальна.
    echo.
)

:: ============================================
:: Запуск сервера
:: ============================================
:start_server

set "NODE_ENV=production"
set "DATA_DIR=%APP_ROOT%\data"
set "PORT=3000"
set "PYTHON_PATH=%APP_ROOT%\python\python.exe"
set "FFMPEG_DIR=%APP_ROOT%\ffmpeg"
set "PLAYWRIGHT_BROWSERS_PATH=%APP_ROOT%\chromium"
set "APP_ROOT_DIR=%APP_ROOT%"

echo  Запускаю сервер...

:: Запускаем сервер в фоне
start /b "" "%NODE_EXE%" "%APP_DIR%\packages\server\dist\index.js"
set SERVER_PID=%errorlevel%

:: Ждём пока сервер запустится
echo  Ожидаю запуск сервера...
set RETRIES=0

:wait_server
timeout /t 1 /nobreak >nul
set /a RETRIES+=1

:: Проверяем доступность сервера
"%NODE_EXE%" -e "fetch('http://localhost:3000/api/auth/status').then(r=>{process.exit(r.ok?0:1)}).catch(()=>process.exit(1))" >nul 2>&1
if %errorlevel% equ 0 goto server_ready

if %RETRIES% lss 15 goto wait_server

echo  [ОШИБКА] Сервер не запустился за 15 секунд.
pause
exit /b 1

:server_ready
echo.
echo  ✓ Flow App запущен: http://localhost:3000
echo.
echo  Открываю браузер...
start http://localhost:3000

echo.
echo  ─────────────────────────────────────
echo  Flow App работает. Не закрывайте это окно.
echo  Для остановки нажмите Ctrl+C или закройте окно.
echo  ─────────────────────────────────────
echo.

:: Ждём завершения (Ctrl+C или закрытие окна)
:: Сервер работает в фоне, просто ждём
:keep_alive
timeout /t 3600 /nobreak >nul
goto keep_alive
