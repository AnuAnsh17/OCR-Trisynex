#!/usr/bin/env bash
PYTHON="./.venv/bin/python"
if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
fi

echo "Starting OCR-Trisynex Web Server on http://127.0.0.1:8000..."
$PYTHON -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
