# ============================================
# Flow App - Build installer
# Runs in CI (GitHub Actions) on Windows
# Expects: npm ci && npm run build already done
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
# 1. Prepare app/ directory from built project
# ============================================
Write-Host "=== Step 1: Preparing app/ ===" -ForegroundColor Yellow

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

Write-Host "Installing server production dependencies..."

# Remove workspace dependency on @flow-app/shared (it's bundled, not from npm)
$serverPkg = Join-Path $serverDir "package.json"
$serverPkgJson = Get-Content $serverPkg -Raw | ConvertFrom-Json
if ($serverPkgJson.dependencies.PSObject.Properties["@flow-app/shared"]) {
    $serverPkgJson.dependencies.PSObject.Properties.Remove("@flow-app/shared")
    $serverPkgJson | ConvertTo-Json -Depth 10 | Set-Content $serverPkg
    Write-Host "Removed @flow-app/shared workspace dep from server package.json"
}

$ErrorActionPreference = "Continue"
Push-Location $serverDir
try { & npm install --omit=dev 2>&1 | Out-Null } finally { Pop-Location }
$ErrorActionPreference = "Stop"

# Link shared package manually (copy dist into node_modules)
$sharedLink = Join-Path $serverDir "node_modules\@flow-app\shared"
New-Item -ItemType Directory -Force -Path $sharedLink | Out-Null
Copy-Item -Recurse "$appDir\packages\shared\*" $sharedLink

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

# package.json
Copy-Item (Join-Path $ProjectRoot "package.json") $appDir

# version.json
$versionJson = @{
    version = $Version
    builtAt = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
} | ConvertTo-Json
Set-Content (Join-Path $appDir "version.json") $versionJson

Write-Host "app/ ready"

# ============================================
# 2. Copy launcher and update-checker
# ============================================
Write-Host ""
Write-Host "=== Step 2: Launcher ===" -ForegroundColor Yellow

Copy-Item (Join-Path $InstallerDir "launcher.bat") $BuildDir
Copy-Item (Join-Path $InstallerDir "update-checker.js") $BuildDir

$icoPath = Join-Path $InstallerDir "FlowApp.ico"
if (Test-Path $icoPath) {
    Copy-Item $icoPath $BuildDir
} else {
    Write-Host "[!] FlowApp.ico not found - installer will have no icon" -ForegroundColor Yellow
}

# ============================================
# 3. Create code-bundle.zip (for auto-updates)
# ============================================
Write-Host ""
Write-Host "=== Step 3: code-bundle.zip ===" -ForegroundColor Yellow

$bundleZip = Join-Path $InstallerDir "code-bundle.zip"
if (Test-Path $bundleZip) { Remove-Item $bundleZip }

Compress-Archive -Path "$appDir\*" -DestinationPath $bundleZip -CompressionLevel Optimal
$bundleSize = (Get-Item $bundleZip).Length / 1MB
Write-Host "code-bundle.zip: $([math]::Round($bundleSize, 1)) MB"

# ============================================
# 4. Compile Inno Setup
# ============================================
Write-Host ""
Write-Host "=== Step 4: Inno Setup ===" -ForegroundColor Yellow

$issFile = Join-Path $InstallerDir "flow-app-setup.iss"

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
    Write-Host "Compiling installer..."
    & $iscc "/DAppVersion=$Version" "/DBuildDir=$BuildDir" "/DOutputDir=$InstallerDir" $issFile

    $setupExe = Get-ChildItem -Path $InstallerDir -Filter "FlowApp-Setup-*.exe" | Select-Object -First 1
    if ($setupExe) {
        $setupSize = $setupExe.Length / 1MB
        Write-Host ""
        Write-Host "=== DONE ===" -ForegroundColor Green
        Write-Host "Installer: $($setupExe.Name)" -ForegroundColor Green
        Write-Host "Size: $([math]::Round($setupSize, 1)) MB" -ForegroundColor Green
    } else {
        Write-Host "[!] Installer not created" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[!] Inno Setup not found" -ForegroundColor Red
    exit 1
}
