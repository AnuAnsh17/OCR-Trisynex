# Quick Launcher for OCR-Trisynex Webapp
$python = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } elseif (Test-Path ".\.venv-indicocr\Scripts\python.exe") { ".\.venv-indicocr\Scripts\python.exe" } else { "python" }

Write-Host "Starting OCR-Trisynex Web Server on http://127.0.0.1:8000..." -ForegroundColor Cyan
& $python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
