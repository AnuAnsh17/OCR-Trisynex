#!/usr/bin/env bash
# ==============================================================================
# OCR-Trisynex Automated Local Installer (Linux / macOS / WSL)
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/AnuAnsh17/OCR-Trisynex/main/install.sh | bash
# ==============================================================================

set -e

echo "=========================================================="
echo "      OCR-Trisynex Automated Local Installer              "
echo "=========================================================="

REPO_NAME="OCR-Trisynex"
REPO_URL="https://github.com/AnuAnsh17/OCR-Trisynex.git"

if [ ! -f "backend/main.py" ]; then
    if [ -d "$REPO_NAME" ]; then
        cd "$REPO_NAME"
    else
        echo "Cloning repository from $REPO_URL..."
        git clone "$REPO_URL"
        cd "$REPO_NAME"
    fi
fi

echo "[1/5] Checking Python environment..."
PYTHON_BIN=""
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "Error: Python 3.10+ is required but not installed." >&2
    exit 1
fi

PY_VERSION=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Found Python version: $PY_VERSION"

echo "[2/5] Setting up virtual environment (.venv)..."
if [ ! -d ".venv" ]; then
    $PYTHON_BIN -m venv .venv
fi
VENV_PYTHON="./.venv/bin/python"
VENV_PIP="./.venv/bin/pip"

$VENV_PYTHON -m pip install --upgrade pip setuptools wheel --quiet

echo "[3/5] Detecting hardware acceleration (GPU / CUDA)..."
if command -v nvidia-smi &>/dev/null && nvidia-smi &>/dev/null; then
    echo "NVIDIA GPU detected. Installing CUDA-accelerated PyTorch..."
    $VENV_PIP install torch torchvision --index-url https://download.pytorch.org/whl/cu124 --quiet
else
    echo "Installing standard PyTorch..."
    $VENV_PIP install torch torchvision --quiet
fi

echo "[4/5] Installing core dependencies from requirements.txt..."
$VENV_PIP install -r requirements.txt --quiet

echo "[5/5] Pre-caching IndicOCR model weights (bodhan-ai/indic-ocr)..."
$VENV_PYTHON scripts/download_model.py

echo ""
echo "=========================================================="
echo "  Installation Completed Successfully!                   "
echo "=========================================================="
echo ""
echo "To start the application:"
echo "  ./run.sh"
echo "Or manually:"
echo "  ./.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
echo ""
