@echo off
echo ===================================
echo   Installing Flow App
echo ===================================
echo.

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found.
    echo Install from https://nodejs.org ^(v18+ required^)
    exit /b 1
)
echo Node.js:
node --version

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python not found.
        echo Install from https://python.org ^(v3.9+ required^)
        exit /b 1
    )
    echo Python:
    py --version
) else (
    echo Python:
    python --version
)

REM Check FFmpeg
where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo.
  echo Downloading FFmpeg...
  mkdir "%~dp0..\bin" 2>nul
  curl -L -o "%~dp0..\bin\ffmpeg.zip" "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
  powershell -command "Expand-Archive -Path '%~dp0..\bin\ffmpeg.zip' -DestinationPath '%~dp0..\bin\ffmpeg-temp' -Force"
  for /d %%i in ("%~dp0..\bin\ffmpeg-temp\*") do (
    copy "%%i\bin\ffmpeg.exe" "%~dp0..\bin\ffmpeg.exe"
    copy "%%i\bin\ffprobe.exe" "%~dp0..\bin\ffprobe.exe"
  )
  rd /s /q "%~dp0..\bin\ffmpeg-temp"
  del "%~dp0..\bin\ffmpeg.zip"
  echo FFmpeg installed to bin/
) else (
  echo FFmpeg: found
)

REM Install npm dependencies
echo.
echo Installing npm dependencies...
call npm install
if errorlevel 1 (
    echo ERROR: npm install failed.
    exit /b 1
)

REM Install Playwright Chromium
echo.
echo Installing Playwright Chromium browser...
call npx playwright install chromium
if errorlevel 1 (
    echo WARNING: Playwright Chromium install failed. Bot features may not work.
)

echo.
echo ===================================
echo   Installation complete!
echo   Run: npm run dev
echo ===================================
