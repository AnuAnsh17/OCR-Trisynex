import os
import sys
import json
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import fitz  # PyMuPDF
from PIL import Image, ImageOps

from huggingface_hub import snapshot_download

logger = logging.getLogger("urja.ocr_service")
logging.basicConfig(level=logging.INFO)

MODEL_REPO = "bodhan-ai/indic-ocr"
_PARSER_INSTANCE = None


def get_indic_ocr_parser():
    global _PARSER_INSTANCE
    if _PARSER_INSTANCE is None:
        logger.info(f"Downloading/resolving snapshot for {MODEL_REPO}...")
        repo_path = snapshot_download(MODEL_REPO)
        if repo_path not in sys.path:
            sys.path.insert(0, repo_path)
        from indic_ocr import IndicOCR
        logger.info("Initializing IndicOCR model instance...")
        _PARSER_INSTANCE = IndicOCR.from_pretrained(repo_path)
        logger.info("IndicOCR model successfully loaded.")
    return _PARSER_INSTANCE


def rasterize_pdf(pdf_path: Path, output_dir: Path, dpi: int = 200) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    image_paths = []
    
    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img_path = output_dir / f"page_{i + 1:03d}.png"
        pix.save(str(img_path))
        image_paths.append(img_path)
        
    doc.close()
    return image_paths


def process_page_images(page_sources: List[Dict[str, Any]], doc_id: str, doc_dir: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Saves:
    - doc_dir / "ocr" / "indicocr_raw.json"
    - doc_dir / "ocr" / "pages" / "page_001.json", etc.
    """
    ocr_dir = doc_dir / "ocr"
    pages_json_dir = ocr_dir / "pages"
    page_images_dir = doc_dir / "pages"
    
    ocr_dir.mkdir(parents=True, exist_ok=True)
    pages_json_dir.mkdir(parents=True, exist_ok=True)
    
    image_paths = []
    for source in page_sources:
        image_path = Path(source["image_path"])
        image_paths.append((image_path, source))
    
    parser = get_indic_ocr_parser()
    page_results = []
    
    for idx, (img_path, source) in enumerate(image_paths, start=1):
        logger.info(f"Running IndicOCR on page {idx}/{len(image_paths)}: {img_path.name}")
        try:
            parsed_data = parser.parse(str(img_path))
            page_data = {
                "status": "completed",
                "document_id": doc_id,
                "source_id": source["source_id"],
                "source_filename": source.get("source_filename", source.get("filename", "")),
                "page_number": source.get("source_page_number", idx),
                "page_order": idx,
                "image_path": str(img_path),
                "source_file": img_path.name,
                "source_path": str(img_path),
                "source_page_number": source.get("source_page_number"),
                "ocr_engine": "IndicOCR",
                "model": MODEL_REPO,
                "result": parsed_data
            }
        except Exception as e:
            logger.error(f"Error running OCR on page {idx}: {e}")
            page_data = {
                "status": "failed",
                "document_id": doc_id,
                "source_id": source["source_id"],
                "source_filename": source.get("source_filename", source.get("filename", "")),
                "page_number": source.get("source_page_number", idx),
                "page_order": idx,
                "image_path": str(img_path),
                "source_file": img_path.name,
                "source_path": str(img_path),
                "source_page_number": source.get("source_page_number"),
                "ocr_engine": "IndicOCR",
                "model": MODEL_REPO,
                "error": str(e),
                "result": None
            }
            
        page_results.append(page_data)
        
        # Save page level ocr json
        page_file = pages_json_dir / f"page_{idx:03d}.json"
        with open(page_file, "w", encoding="utf-8") as f:
            json.dump(page_data, f, ensure_ascii=False, indent=2)
            
    combined_raw = {
        "document_id": doc_dir.name,
        "ocr_engine": "IndicOCR",
        "model": MODEL_REPO,
        "status": "completed_with_errors" if any(p["status"] == "failed" for p in page_results) else "completed",
        "page_count": len(image_paths),
        "pages": page_results
    }
    
    combined_file = ocr_dir / "indicocr_raw.json"
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(combined_raw, f, ensure_ascii=False, indent=2)
        
    return combined_raw, page_results


def prepare_sources(sources: List[Dict[str, Any]], doc_dir: Path, dpi: int = 200) -> List[Dict[str, Any]]:
    """Convert PDFs to ordered page images and pass uploaded images through as pages."""
    pages_dir = doc_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    prepared = []
    for source in sources:
        source_path = Path(source["path"])
        if source["type"] == "pdf":
            rendered = rasterize_pdf(source_path, pages_dir / source["source_id"], dpi=dpi)
            for page_number, image_path in enumerate(rendered, start=1):
                prepared.append({**source, "source_page_number": page_number, "image_path": str(image_path)})
        else:
            target = pages_dir / source_path.name
            with Image.open(source_path) as image:
                ImageOps.exif_transpose(image).convert("RGB").save(target, format="PNG")
            prepared.append({**source, "source_page_number": 1, "image_path": str(target)})
    return prepared


def process_document_ocr(pdf_path: Path, doc_dir: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Compatibility wrapper for older scripts that submit one PDF."""
    source = {"source_id": "source_001", "source_filename": pdf_path.name, "type": "pdf", "path": str(pdf_path)}
    pages = prepare_sources([source], doc_dir)
    return process_page_images(pages, doc_dir.name, doc_dir)
