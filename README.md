# OCR-Trisynex (Urja)

Lossless, local-first document ingestion, OCR, and analysis system with native IndicOCR and fast digital extraction pipeline.

## Overview
- **FastAPI Backend:** Local document ingestion pipeline with high-throughput processing.
- **Hybrid OCR Pipeline:** Fast vector PDF extraction (<10ms) paired with IndicOCR (`bodhan-ai/indic-ocr`) for scanned pages.
- **Domain Modeling & Semantics:** Lossless generic document structuring with specialized electricity bill semantic adapter and deterministic validation checks.
- **Frontend Dashboard:** Interactive local web dashboard for document upload, analysis, table inspection, and JSON export.

## Quickstart

### Backend Setup
```powershell
# Activate environment
.\.venv-indicocr\Scripts\Activate.ps1

# Run server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Running Tests
```powershell
python -m unittest tests/test_document_pipeline.py
```
