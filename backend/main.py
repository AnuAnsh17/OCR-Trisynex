import os
import time
import json
import uuid
import shutil
import logging
from typing import List, Any, Optional
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import torch

from backend.services.ocr_service import prepare_sources, process_page_images, get_indic_ocr_parser
from backend.services.generic_builder import GenericDocumentBuilder
from backend.services.semantic.electricity_adapter import ElectricityBillAdapter
from backend.services.validator import UrjaValidator

logger = logging.getLogger("smart_utility.main")
logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = BASE_DIR / "data" / "documents"
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Smart Utility - Lossless Local Document Ingestion & Analysis System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

generic_builder = GenericDocumentBuilder()
electricity_adapter = ElectricityBillAdapter()
validator = UrjaValidator()


@app.get("/api/health")
def health_check():
    """Health check endpoint showing acceleration and device status."""
    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU"
    return {
        "status": "ready",
        "acceleration": "cuda" if cuda_available else "cpu",
        "device_name": device_name,
        "engine": "IndicOCR + DigitalVector"
    }


@app.post("/api/ingest")
def ingest_documents(
    files: List[UploadFile] = File(...), 
    group_images: bool = Form(False),
    force_ocr: bool = Form(False)
):
    t_req_start = time.perf_counter()
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one PDF or image.")
    batch_id = uuid.uuid4().hex[:12]
    extensions = {".pdf": "pdf", ".png": "image", ".jpg": "image", ".jpeg": "image"}
    groups, image_group = [], []
    image_items = []
    for order, upload in enumerate(files, start=1):
        ext = Path(upload.filename or "").suffix.lower()
        if ext not in extensions:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {upload.filename}")
        item = {"source_id": f"source_{order:03d}", "filename": upload.filename, "type": extensions[ext], "order": order, "upload": upload}
        if item["type"] == "pdf":
            groups.append((order, [item]))
        elif group_images:
            image_items.append(item)
        else:
            groups.append((order, [item]))
    if image_items:
        groups.append((min(item["order"] for item in image_items), image_items))
    groups.sort(key=lambda entry: entry[0])
    groups = [group for _, group in groups]

    documents, manifest_documents = [], []
    for group in groups:
        t_doc_start = time.perf_counter()
        doc_id = uuid.uuid4().hex[:12]
        doc_dir = DOCUMENTS_DIR / doc_id
        source_dir = doc_dir / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        sources = []
        for item in group:
            safe_original_name = Path(item["filename"]).name
            target = source_dir / f"{item['source_id']}__{safe_original_name}"
            with target.open("wb") as out:
                shutil.copyfileobj(item["upload"].file, out)
            sources.append({"source_id": item["source_id"], "filename": item["filename"], "type": item["type"], "order": item["order"], "path": str(target)})
        manifest_doc = {"document_id": doc_id, "sources": [{k: v for k, v in src.items() if k != "path"} for src in sources], "pages": []}
        try:
            t_prep_start = time.perf_counter()
            prepared = prepare_sources(sources, doc_dir)
            t_prep_ms = round((time.perf_counter() - t_prep_start) * 1000, 2)

            for page_order, page in enumerate(prepared, start=1):
                manifest_doc["pages"].append({"page_id": f"page_{page_order:03d}", "source_id": page["source_id"], "page_number": page["source_page_number"], "order": page_order, "image_path": page["image_path"]})
            
            t_ocr_start = time.perf_counter()
            raw, _ = process_page_images(prepared, doc_id, doc_dir, force_ocr=force_ocr)
            t_ocr_ms = round((time.perf_counter() - t_ocr_start) * 1000, 2)

            raw["document_id"] = doc_id
            raw["sources"] = manifest_doc["sources"]
            (doc_dir / "ocr" / "indicocr_raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
            for folder in ("normalized", "semantic", "validation"):
                (doc_dir / folder).mkdir(parents=True, exist_ok=True)
            
            t_build_start = time.perf_counter()
            doc = generic_builder.build(doc_id, ", ".join(x["filename"] for x in sources), raw)
            generic = doc.model_dump()
            (doc_dir / "normalized" / "document.json").write_text(json.dumps(generic, ensure_ascii=False, indent=2), encoding="utf-8")
            
            semantic_obj = electricity_adapter.adapt(doc) if doc.document.document_type == "electricity_bill" else None
            semantic = semantic_obj.model_dump() if semantic_obj else {"domain": None, "fields": [], "evidence": []}
            semantic_name = "electricity_bill.json" if semantic_obj else "generic_semantic.json"
            (doc_dir / "semantic" / semantic_name).write_text(json.dumps(semantic, ensure_ascii=False, indent=2), encoding="utf-8")
            
            validation = validator.validate(semantic_obj).model_dump() if semantic_obj else {"status": "not_applicable", "checks": []}
            (doc_dir / "validation" / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
            t_build_ms = round((time.perf_counter() - t_build_start) * 1000, 2)

            status = "failed" if raw["page_count"] and all(p["status"] == "failed" for p in raw["pages"]) else raw["status"]
            manifest_doc["status"] = status
            for manifest_page, ocr_page in zip(manifest_doc["pages"], raw["pages"]):
                manifest_page["status"] = ocr_page["status"]
            manifest_documents.append(manifest_doc)

            doc_total_ms = round((time.perf_counter() - t_doc_start) * 1000, 2)
            timing_info = {
                "prepare_ms": t_prep_ms,
                "ocr_ms": t_ocr_ms,
                "build_ms": t_build_ms,
                "total_ms": doc_total_ms
            }

            documents.append({
                "document_id": doc_id, 
                "status": status, 
                "document": generic, 
                "semantic": semantic, 
                "validation": validation, 
                "raw_ocr": raw,
                "timing": timing_info
            })
        except Exception as error:
            logger.exception("Document processing failed: %s", doc_id)
            manifest_doc.update({"status": "failed", "error": str(error)})
            manifest_documents.append(manifest_doc)
            documents.append({"document_id": doc_id, "status": "failed", "error": str(error)})
    
    manifest = {"batch_id": batch_id, "documents": manifest_documents}
    (DOCUMENTS_DIR / f"{batch_id}_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    
    total_batch_ms = round((time.perf_counter() - t_req_start) * 1000, 2)
    response = {
        "batch_id": batch_id, 
        "status": "completed_with_errors" if any(d["status"] != "completed" for d in documents) else "completed", 
        "documents": documents,
        "timing_ms": total_batch_ms
    }
    if len(documents) == 1:
        response.update(documents[0])
    return JSONResponse(content=response)


@app.get("/api/documents/{document_id}/normalized")
def get_normalized_document(document_id: str):
    json_path = DOCUMENTS_DIR / document_id / "normalized" / "document.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Normalized document not found.")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/documents/{document_id}/semantic")
def get_semantic_document(document_id: str):
    semantic_dir = DOCUMENTS_DIR / document_id / "semantic"
    json_path = semantic_dir / "electricity_bill.json"
    if not json_path.exists():
        json_path = semantic_dir / "generic_semantic.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Semantic document not found.")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/documents/{document_id}/raw")
def get_raw_ocr_document(document_id: str):
    raw_path = DOCUMENTS_DIR / document_id / "ocr" / "indicocr_raw.json"
    if not raw_path.exists():
        raise HTTPException(status_code=404, detail="Raw OCR document not found.")
    with open(raw_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/documents/{document_id}/validation")
def get_validation_document(document_id: str):
    val_path = DOCUMENTS_DIR / document_id / "validation" / "validation.json"
    if not val_path.exists():
        raise HTTPException(status_code=404, detail="Validation document not found.")
    with open(val_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/documents/{document_id}/source")
def get_source_pdf(document_id: str):
    source_dir = DOCUMENTS_DIR / document_id / "source"
    source_files = sorted(path for path in source_dir.glob("source_*") if path.is_file()) if source_dir.exists() else []
    legacy_source = source_dir / "original.pdf"
    if not source_files and legacy_source.exists():
        source_files = [legacy_source]
    if not source_files:
        raise HTTPException(status_code=404, detail="Source file not found.")
    path = source_files[0]
    return FileResponse(path, filename=path.name)


FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")
