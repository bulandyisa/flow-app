# ============================================
# Flow App — Полная сборка установщика
# Запускается в CI (GitHub Actions) на Windows
# Предполагает что npm ci && npm run build уже выполнены
# ============================================

param(
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot  # flow-app/
$InstallerDir = $PSScriptRoot                      # flow-app/installer/
$BuildDir = Join-Path $InstallerDir "build"

Write-Host "=== Flow App Installer Build ===" -ForegroundColor Cyan
Write-Host "Version: $Version"
Write-Host "Project: $ProjectRoot"
Write-Host "Build: $BuildDir"
Write-Host ""

# ============================================
# 1. Формируем app/ директорию из уже собранного проекта
# ============================================
Write-Host "=== Шаг 1: Формирование app/ ===" -ForegroundColor Yellow

$appDir = Join-Path $BuildDir "app"
if (Test-Path $appDir) { Remove-Item -Recurse -Force $appDir }
New-Item -ItemType Directory -Force -Path $appDir | Out-Null

# shared/dist
$sharedDist = Join-Path $appDir "packages\shared"
New-Item -ItemType Directory -Force -Path "$sharedDist\dist" | Out-Null
Copy-Item -Recurse (Join-Path $ProjectRoot "packages\shared\dist\*") "$sharedDist\dist\"
Copy-Item (Join-Path $ProjectRoot "packages\shared\package.json") $sharedDist

# server/dist + production deps
$serverDir = Join-Path $appDir "packages\server"
New-Item -ItemType Directory -Force -Path "$serverDir\dist" | Out-Null
Copy-Item -Recurse (Join-Path $ProjectRoot "packages\server\dist\*") "$serverDir\dist\"
Copy-Item (Join-Path $ProjectRoot "packages\server\package.json") $serverDir

Write-Host "Устанавливаю production зависимости сервера..."
$nodeExe = Join-Path $BuildDir "node\node.exe"
$npmCmd = Join-Path $BuildDir "node\npm.cmd"

if (Test-Path $npmCmd) {
    # Используем portable Node.js из build/
    Push-Location $serverDir
    try { & $npmCmd install --omit=dev 2>&1 | Out-Null } finally { Pop-Location }
} else {
    # Fallback: системный npm
    Push-Location $serverDir
    try { & npm install --omit=dev 2>&1 | Out-Null } finally { Pop-Location }
}

# client/dist
$clientDist = Join-Path $appDir "packages\client\dist"
New-Item -ItemType Directory -Force -Path $clientDist | Out-Null
Copy-Item -Recurse (Join-Path $ProjectRoot "packages\client\dist\*") $clientDist

# bot/
$botDir = Join-Path $appDir "bot"
New-Item -ItemType Directory -Force -Path $botDir | Out-Null
Copy-Item (Join-Path $ProjectRoot "bot\flow_bot.py") $botDir
if (Test-Path (Join-Path $ProjectRoot "bot\r2_storage.py")) {
    Copy-Item (Join-Path $ProjectRoot "bot\r2_storage.py") $botDir
}
if (Test-Path (Join-Path $ProjectRoot "bot\run_safe.bat")) {
    Copy-Item (Join-Path $ProjectRoot "bot\run_safe.bat") $botDir
}

# rules/
$rulesDir = Join-Path $appDir "rules"
New-Item -ItemType Directory -Force -Path $rulesDir | Out-Null
Copy-Item (Join-Path $ProjectRoot "rules\*") $rulesDir

# package.json (для определения версии в dev mode)
Copy-Item (Join-Path $ProjectRoot "package.json") $appDir

# version.json
$versionJson = @{
    version = $Version
    builtAt = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
} | ConvertTo-Json
Set-Content (Join-Path $appDir "version.json") $versionJson

Write-Host "app/ сформирована"

# ============================================
# 2. Копируем лаунчер и update-checker
# ============================================
Write-Host ""
Write-Host "=== Шаг 2: Лаунчер ===" -ForegroundColor Yellow

Copy-Item (Join-Path $InstallerDir "launcher.bat") $BuildDir
Copy-Item (Join-Path $InstallerDir "update-checker.js") $BuildDir

$icoPath = Join-Path $InstallerDir "FlowApp.ico"
if (Test-Path $icoPath) {
    Copy-Item $icoPath $BuildDir
} else {
    Write-Host "[!] FlowApp.ico не найден — установщик будет без иконки" -ForegroundColor Yellow
}

# ============================================
# 3. Создаём code-bundle.zip (для автообновлений)
# ============================================
Write-Host ""
Write-Host "=== Шаг 3: code-bundle.zip ===" -ForegroundColor Yellow

$bundleZip = Join-Path $InstallerDir "code-bundle.zip"
if (Test-Path $bundleZip) { Remove-Item $bundleZip }

Compress-Archive -Path "$appDir\*" -DestinationPath $bundleZip -CompressionLevel Optimal
$bundleSize = (Get-Item $bundleZip).Length / 1MB
Write-Host "code-bundle.zip: $([math]::Round($bundleSize, 1)) MB"

# ============================================
# 4. Компилируем Inno Setup (если доступен)
# ============================================
Write-Host ""
Write-Host "=== Шаг 4: Inno Setup ===" -ForegroundColor Yellow

$issFile = Join-Path $InstallerDir "flow-app-setup.iss"

# Ищем ISCC.exe
$iscc = $null
$isccPaths = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "C:\ProgramData\chocolatey\bin\ISCC.exe"
)
foreach ($p in $isccPaths) {
    if (Test-Path $p) { $iscc = $p; break }
}

if ($iscc) {
    Write-Host "Inno Setup: $iscc"
    Write-Host "Компилирую установщик..."
    & $iscc "/DAppVersion=$Version" "/DBuildDir=$BuildDir" "/DOutputDir=$InstallerDir" $issFile

    $setupExe = Get-ChildItem -Path $InstallerDir -Filter "FlowApp-Setup-*.exe" | Select-Object -First 1
    if ($setupExe) {
        $setupSize = $setupExe.Length / 1MB
        Write-Host ""
        Write-Host "=== ГОТОВО ===" -ForegroundColor Green
        Write-Host "Установщик: $($setupExe.Name)" -ForegroundColor Green
        Write-Host "Размер: $([math]::Round($setupSize, 1)) MB" -ForegroundColor Green
    } else {
        Write-Host "[!] Установщик не создан" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[!] Inno Setup не найден — .exe не создан" -ForegroundColor Red
    Write-Host "    code-bundle.zip создан для автообновлений."
    exit 1
}
