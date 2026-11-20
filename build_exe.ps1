# Build a portable AniShade.exe with PyInstaller
#
#   powershell -ExecutionPolicy Bypass -File build_exe.ps1
#   powershell -ExecutionPolicy Bypass -File build_exe.ps1 -OneDir
#
param(
    [switch]$OneDir,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==> Instalando dependencias" -ForegroundColor Cyan
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt pyinstaller

if (-not (Test-Path "assets/anishade.ico")) {
    Write-Host "==> Gerando icone" -ForegroundColor Cyan
    $env:QT_QPA_PLATFORM = "offscreen"
    & $Python tools/make_icon.py
    Remove-Item Env:QT_QPA_PLATFORM
}

$mode = if ($OneDir) { "--onedir" } else { "--onefile" }

Write-Host "==> PyInstaller ($mode)" -ForegroundColor Cyan
& $Python -m PyInstaller `
    --noconfirm --clean --windowed $mode `
    --name AniShade `
    --icon "assets/anishade.ico" `
    --add-data "vendor/anime4k;vendor/anime4k" `
    --add-data "vendor/anime4k_fx;vendor/anime4k_fx" `
    --add-data "assets;assets" `
    --hidden-import "PySide6.QtSvg" `
    run.py

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller falhou."
}

Write-Host ""
Write-Host "Pronto: dist\AniShade.exe" -ForegroundColor Green
Write-Host "Os shaders Anime4K vao embutidos; o ReShade e baixado no primeiro uso."
