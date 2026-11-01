# ==============================================================================
# OCR-Trisynex Automated Local Installer (Windows PowerShell)
# Usage:
#   irm https://raw.githubusercontent.com/AnuAnsh17/OCR-Trisynex/main/install.ps1 | iex
#   or: powershell -ExecutionPolicy Bypass -File install.ps1
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "      OCR-Trisynex Automated Local Installer              " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Ensure Repository Directory
$repoName = "OCR-Trisynex"
$repoUrl = "https://github.com/AnuAnsh17/OCR-Trisynex.git"

if (-not (Test-Path "backend/main.py")) {
    if (Test-Path $repoName) {
        Set-Location $repoName
    } else {
        Write-Host "Cloning repository from $repoUrl..." -ForegroundColor Yellow
        git clone $repoUrl
        Set-Location $repoName
    }
}

Write-Host "[1/5] Checking Python environment..." -ForegroundColor Green
$pythonCmd = $null
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
} else {
    Write-Error "Python 3.10+ is required but not found in PATH. Please install Python 3.10+ and re-run."
}

$pyVersion = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Found Python version: $pyVersion" -ForegroundColor Gray

# 2. Virtual Environment Setup
Write-Host "[2/5] Setting up virtual environment (.venv)..." -ForegroundColor Green
if (-not (Test-Path ".venv")) {
    & $pythonCmd -m venv .venv
}
$venvPython = ".\.venv\Scripts\python.exe"
$venvPip = ".\.venv\Scripts\pip.exe"

# Upgrade pip
& $venvPython -m pip install --upgrade pip setuptools wheel --quiet

# 3. Detect Hardware Acceleration (CUDA)
Write-Host "[3/5] Detecting hardware acceleration (GPU / CUDA)..." -ForegroundColor Green
$hasGpu = $false
try {
    $smi = nvidia-smi 2>$null
    if ($LASTEXITCODE -eq 0) {
        $hasGpu = $true
        Write-Host "NVIDIA GPU detected. Installing CUDA-accelerated PyTorch..." -ForegroundColor Cyan
        & $venvPip install torch torchvision --index-url https://download.pytorch.org/whl/cu124 --quiet
    }
} catch {
    $hasGpu = $false
}

if (-not $hasGpu) {
    Write-Host "No NVIDIA GPU detected. Installing standard CPU PyTorch..." -ForegroundColor Yellow
    & $venvPip install torch torchvision --quiet
}

# 4. Install Dependencies
Write-Host "[4/5] Installing core dependencies from requirements.txt..." -ForegroundColor Green
& $venvPip install -r requirements.txt --quiet

# 5. Pre-warm / Cache Model Snapshot
Write-Host "[5/5] Pre-caching IndicOCR model weights (bodhan-ai/indic-ocr)..." -ForegroundColor Green
& $venvPython scripts/download_model.py

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  Installation Completed Successfully!                   " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "`nTo start the application:" -ForegroundColor White
Write-Host "  .\run.ps1" -ForegroundColor Yellow
Write-Host "Or manually:" -ForegroundColor White
Write-Host "  .\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload`n" -ForegroundColor Gray
