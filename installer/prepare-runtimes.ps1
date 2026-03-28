# ============================================
# Flow App — Подготовка рантаймов для установщика
# Запускается в CI (GitHub Actions) на Windows
# Скачивает и настраивает: Node.js, Python, FFmpeg, Playwright Chromium
# ============================================

param(
    [string]$BuildDir = ".\build",
    [string]$NodeVersion = "22.14.0",
    [string]$PythonVersion = "3.12.9",
    [string]$FFmpegRelease = "latest"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Flow App: Подготовка рантаймов ===" -ForegroundColor Cyan
Write-Host "Build dir: $BuildDir"
Write-Host "Node.js: $NodeVersion"
Write-Host "Python: $PythonVersion"
Write-Host ""

# Создаём build директорию
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

# ============================================
# 1. Node.js Portable
# ============================================
Write-Host "--- [1/4] Node.js portable ---" -ForegroundColor Green

$nodeDir = Join-Path $BuildDir "node"
$nodeZip = Join-Path $BuildDir "node.zip"
$nodeUrl = "https://nodejs.org/dist/v$NodeVersion/node-v$NodeVersion-win-x64.zip"

if (-not (Test-Path (Join-Path $nodeDir "node.exe"))) {
    Write-Host "Скачиваю Node.js v$NodeVersion..."
    Invoke-WebRequest -Uri $nodeUrl -OutFile $nodeZip -UseBasicParsing

    Write-Host "Распаковываю..."
    Expand-Archive -Path $nodeZip -DestinationPath $BuildDir -Force

    # Переименовываем папку
    $extracted = Get-ChildItem -Path $BuildDir -Directory -Filter "node-v*" | Select-Object -First 1
    if ($extracted) {
        if (Test-Path $nodeDir) { Remove-Item -Recurse -Force $nodeDir }
        Rename-Item $extracted.FullName $nodeDir
    }

    Remove-Item $nodeZip -Force
    Write-Host "Node.js OK: $(& (Join-Path $nodeDir 'node.exe') --version)"
} else {
    Write-Host "Node.js уже подготовлен."
}

# ============================================
# 2. Python Embedded
# ============================================
Write-Host ""
Write-Host "--- [2/4] Python embedded ---" -ForegroundColor Green

$pythonDir = Join-Path $BuildDir "python"
$pythonZip = Join-Path $BuildDir "python.zip"
$pyMajorMinor = $PythonVersion.Split('.')[0..1] -join ''
$pythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"

if (-not (Test-Path (Join-Path $pythonDir "python.exe"))) {
    Write-Host "Скачиваю Python $PythonVersion embedded..."
    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonZip -UseBasicParsing

    Write-Host "Распаковываю..."
    New-Item -ItemType Directory -Force -Path $pythonDir | Out-Null
    Expand-Archive -Path $pythonZip -DestinationPath $pythonDir -Force
    Remove-Item $pythonZip -Force

    # Включаем import site (нужно для pip)
    $pthFile = Join-Path $pythonDir "python${pyMajorMinor}._pth"
    if (Test-Path $pthFile) {
        $content = Get-Content $pthFile
        $content = $content -replace '#import site', 'import site'
        Set-Content $pthFile $content
        Write-Host "Включён import site в $pthFile"
    }

    # Устанавливаем pip
    Write-Host "Устанавливаю pip..."
    $getPipUrl = "https://bootstrap.pypa.io/get-pip.py"
    $getPipPath = Join-Path $BuildDir "get-pip.py"
    Invoke-WebRequest -Uri $getPipUrl -OutFile $getPipPath -UseBasicParsing
    & (Join-Path $pythonDir "python.exe") $getPipPath --no-warn-script-location 2>&1
    Remove-Item $getPipPath -Force

    # Устанавливаем зависимости бота
    Write-Host "Устанавливаю playwright..."
    $pythonExe = Join-Path $pythonDir "python.exe"
    & $pythonExe -m pip install playwright boto3 --no-warn-script-location 2>&1

    Write-Host "Python OK: $(& $pythonExe --version)"
} else {
    Write-Host "Python уже подготовлен."
}

# ============================================
# 3. Playwright Chromium
# ============================================
Write-Host ""
Write-Host "--- [3/4] Playwright Chromium ---" -ForegroundColor Green

$chromiumDir = Join-Path $BuildDir "chromium"

if (-not (Test-Path $chromiumDir) -or (Get-ChildItem $chromiumDir -ErrorAction SilentlyContinue).Count -eq 0) {
    Write-Host "Устанавливаю Playwright Chromium..."
    $env:PLAYWRIGHT_BROWSERS_PATH = $chromiumDir
    $pythonExe = Join-Path $pythonDir "python.exe"
    & $pythonExe -m playwright install chromium 2>&1
    Write-Host "Chromium OK"
} else {
    Write-Host "Chromium уже установлен."
}

# ============================================
# 4. FFmpeg
# ============================================
Write-Host ""
Write-Host "--- [4/4] FFmpeg ---" -ForegroundColor Green

$ffmpegDir = Join-Path $BuildDir "ffmpeg"

if (-not (Test-Path (Join-Path $ffmpegDir "ffmpeg.exe"))) {
    Write-Host "Скачиваю FFmpeg..."

    # Получаем URL последнего релиза
    $ffmpegZip = Join-Path $BuildDir "ffmpeg.zip"
    $ffmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

    Invoke-WebRequest -Uri $ffmpegUrl -OutFile $ffmpegZip -UseBasicParsing

    Write-Host "Распаковываю..."
    Expand-Archive -Path $ffmpegZip -DestinationPath $BuildDir -Force

    # Находим папку с бинарниками
    New-Item -ItemType Directory -Force -Path $ffmpegDir | Out-Null
    $ffmpegBin = Get-ChildItem -Path $BuildDir -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
    if ($ffmpegBin) {
        Copy-Item $ffmpegBin.FullName (Join-Path $ffmpegDir "ffmpeg.exe")
        $ffprobeBin = Get-ChildItem -Path $BuildDir -Recurse -Filter "ffprobe.exe" | Select-Object -First 1
        if ($ffprobeBin) {
            Copy-Item $ffprobeBin.FullName (Join-Path $ffmpegDir "ffprobe.exe")
        }
    }

    # Чистим распакованные файлы
    Get-ChildItem -Path $BuildDir -Directory -Filter "ffmpeg-*" | Remove-Item -Recurse -Force
    Remove-Item $ffmpegZip -Force -ErrorAction SilentlyContinue

    Write-Host "FFmpeg OK"
} else {
    Write-Host "FFmpeg уже подготовлен."
}

# ============================================
# Итог
# ============================================
Write-Host ""
Write-Host "=== Рантаймы подготовлены ===" -ForegroundColor Cyan

$sizes = @{
    "Node.js" = (Get-ChildItem -Recurse (Join-Path $BuildDir "node") | Measure-Object -Property Length -Sum).Sum / 1MB
    "Python"  = (Get-ChildItem -Recurse (Join-Path $BuildDir "python") | Measure-Object -Property Length -Sum).Sum / 1MB
    "Chromium" = (Get-ChildItem -Recurse (Join-Path $BuildDir "chromium") -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB
    "FFmpeg"  = (Get-ChildItem -Recurse (Join-Path $BuildDir "ffmpeg") | Measure-Object -Property Length -Sum).Sum / 1MB
}

foreach ($item in $sizes.GetEnumerator()) {
    Write-Host ("  {0}: {1:N0} MB" -f $item.Key, $item.Value)
}

$total = ($sizes.Values | Measure-Object -Sum).Sum
Write-Host ("  ИТОГО: {0:N0} MB" -f $total) -ForegroundColor Yellow
