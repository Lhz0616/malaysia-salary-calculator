# Automated Build & Installer Generator Script for Windows
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "==> 1. Syncing dependencies with uv..." -ForegroundColor Cyan
uv sync --all-groups

Write-Host "==> 2. Building executable with PyInstaller & UPX..." -ForegroundColor Cyan
uv run pyinstaller --noconfirm --onefile --windowed `
    --name "MalaysianSalaryCalculator" `
    --icon "src/icon/app_icon.ico" `
    --add-data "src/assets;assets" `
    --add-data "src/icon;icon" `
    src/main.py

$distDir = "dist"
$dataTargetDir = Join-Path $distDir ".data"

Write-Host "==> 3. Copying src/data JSON files to .data directory alongside .exe..." -ForegroundColor Cyan
if (Test-Path $dataTargetDir) {
    Remove-Item -Path $dataTargetDir -Recurse -Force
}
New-Item -ItemType Directory -Path $dataTargetDir -Force | Out-Null
Copy-Item -Path "src/data/*" -Destination $dataTargetDir -Recurse -Force

Write-Host "==> 4. Checking for Inno Setup Compiler (ISCC)..." -ForegroundColor Cyan
$isccCmd = Get-Command "iscc.exe" -ErrorAction SilentlyContinue
$isccPath = $null

if ($isccCmd) {
    $isccPath = $isccCmd.Source
} else {
    $possiblePaths = @(
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    )
    foreach ($p in $possiblePaths) {
        if (Test-Path $p) {
            $isccPath = $p
            break
        }
    }
}

if ($isccPath) {
    Write-Host "==> Compiling installer with Inno Setup ($isccPath)..." -ForegroundColor Green
    if ($env:APP_VERSION) {
        Write-Host "--> Setting installer version to $env:APP_VERSION" -ForegroundColor Green
        & $isccPath /DMyAppVersion="$env:APP_VERSION" installer.iss
    } else {
        & $isccPath installer.iss
    }
    Write-Host "==> Setup installer created in Output/ directory!" -ForegroundColor Green
} else {
    Write-Host "--> ISCC not found. Creating standalone ZIP package instead..." -ForegroundColor Yellow
    $zipPath = Join-Path $distDir "MalaysianSalaryCalculator-Windows.zip"
    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

    $filesToZip = Get-ChildItem -Path $distDir | Where-Object { $_.Name -ne "MalaysianSalaryCalculator-Windows.zip" } | Select-Object -ExpandProperty FullName
    Compress-Archive -Path $filesToZip -DestinationPath $zipPath
    Write-Host "==> ZIP Package created at $zipPath" -ForegroundColor Green
}

Write-Host "==> 5. Creating standalone ZIP package..." -ForegroundColor Cyan
Compress-Archive -Path "dist/*" -DestinationPath "Output/MalaysianSalaryCalculator-Windows.zip"

Write-Host "Done!" --ForegroundColor Green