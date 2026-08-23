# Novel Manager - one-click desktop installer build script
# Usage: run .\build.ps1 in this directory (PowerShell)
$ErrorActionPreference = "Continue"

# China mirrors to avoid Electron download failures
$env:ELECTRON_MIRROR = "https://npmmirror.com/mirrors/electron/"
$env:ELECTRON_BUILDER_BINARIES_MIRROR = "https://npmmirror.com/mirrors/electron-builder-binaries/"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# Auto-activate Python venv if present (works with uv-created venv)
$venvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) { & $venvActivate }

function Invoke-Cmd {
    param([string]$Command, [string[]]$CmdArgs)
    Write-Host ">> $Command $($CmdArgs -join ' ')"
    & $Command @CmdArgs
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Host "Command failed (exit code $exitCode): $Command" -ForegroundColor Red
        exit $exitCode
    }
}

Write-Host "=== [1/4] Build frontend ===" -ForegroundColor Cyan
Set-Location (Join-Path $ProjectRoot "frontend")
Invoke-Cmd "npm" @("install")
Invoke-Cmd "npm" @("run", "build")
Write-Host "[OK] Frontend build done: frontend/dist/" -ForegroundColor Green

Write-Host "=== [2/4] Package backend (PyInstaller) ===" -ForegroundColor Cyan
Set-Location (Join-Path $ProjectRoot "backend")
Invoke-Cmd "python" @("-m", "pip", "install", "-r", "requirements.txt", "--quiet")
Invoke-Cmd "python" @("-m", "PyInstaller", "build.spec", "--noconfirm")
Write-Host "[OK] Backend packaged: backend/dist/novel-backend.exe" -ForegroundColor Green

Write-Host "=== [3/4] Install Electron dependencies ===" -ForegroundColor Cyan
Set-Location (Join-Path $ProjectRoot "desktop")
Invoke-Cmd "npm" @("install")
Write-Host "[OK] Electron dependencies ready" -ForegroundColor Green

Write-Host "=== [4/4] Generate installer (electron-builder) ===" -ForegroundColor Cyan
Invoke-Cmd "npx" @("electron-builder", "--win", "--x64")

$installer = Get-ChildItem (Join-Path $ProjectRoot "desktop\release") -Filter "*Setup*.exe" | Select-Object -First 1
if ($installer) {
    $fileSize = [math]::Round($installer.Length / 1MB, 1).ToString()
    Write-Host "[OK] Installer generated!" -ForegroundColor Green
    Write-Host ("  " + $installer.Name + " (" + $fileSize + " MB)") -ForegroundColor Green
} else {
    Write-Host "Installer not found, check electron-builder output above." -ForegroundColor Red
    exit 1
}
