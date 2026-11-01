import os
import sys
import json
import time
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import fitz  # PyMuPDF

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
        logger.info(f"Model repository path: {repo_path}")
        if repo_path not in sys.path:
            sys.path.insert(0, repo_path)
        from indic_ocr import IndicOCR
        logger.info("Initializing IndicOCR model instance...")
        _PARSER_INSTANCE = IndicOCR.from_pretrained(repo_path)
        logger.info("IndicOCR model successfully loaded.")
    return _PARSER_INSTANCE


def rasterize_pdf(pdf_path: Path, output_dir: Path, dpi: int = 200) -> List[Path]:
    """
    Rasterize PDF pages to PNG image files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    image_paths = []
    
    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img_path = output_dir / f"page_{i + 1}.png"
        pix.save(str(img_path))
        image_paths.append(img_path)
        
    doc.close()
    return image_paths


def run_ocr_on_pdf(pdf_path: Path, base_data_dir: Path, doc_id: str = None) -> Tuple[str, Path, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Runs local IndicOCR on uploaded PDF.
    Saves raw page outputs and combined indicocr_raw.json in data/ocr_results/<document_id>/
    Returns: (document_id, raw_dir_path, list_of_page_results, combined_indicocr_raw)
    """
    if doc_id is None:
        doc_id = uuid.uuid4().hex[:12]
        
    uploads_dir = base_data_dir / "uploads"
    ocr_results_dir = base_data_dir / "ocr_results" / doc_id
    page_images_dir = uploads_dir / doc_id / "pages"
    
    ocr_results_dir.mkdir(parents=True, exist_ok=True)
    page_images_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Rasterizing PDF: {pdf_path}")
    image_paths = rasterize_pdf(pdf_path, page_images_dir)
    
    parser = get_indic_ocr_parser()
    page_results = []
    
    for idx, img_path in enumerate(image_paths, start=1):
        logger.info(f"Running IndicOCR on page {idx}/{len(image_paths)}: {img_path.name}")
        try:
            parsed_data = parser.parse(str(img_path))
            page_data = {
                "page_number": idx,
                "source_file": img_path.name,
                "source_path": str(img_path),
                "ocr_engine": "IndicOCR",
                "model": MODEL_REPO,
                "result": parsed_data
            }
        except Exception as e:
            logger.error(f"Error running OCR on page {idx}: {e}")
            page_data = {
                "page_number": idx,
                "source_file": img_path.name,
                "source_path": str(img_path),
                "ocr_engine": "IndicOCR",
                "model": MODEL_REPO,
                "error": str(e),
                "result": {"blocks": [], "markdown": ""}
            }
            
        page_results.append(page_data)
        
        # Save individual page json
        page_json_file = ocr_results_dir / f"page_{idx}.json"
        with open(page_json_file, "w", encoding="utf-8") as f:
            json.dump(page_data, f, ensure_ascii=False, indent=2)
            
    combined_raw = {
        "document_id": doc_id,
        "ocr_engine": "IndicOCR",
        "model": MODEL_REPO,
        "source_pdf": pdf_path.name,
        "page_count": len(image_paths),
        "pages": page_results
    }
    
    combined_json_file = ocr_results_dir / "indicocr_raw.json"
    with open(combined_json_file, "w", encoding="utf-8") as f:
        json.dump(combined_raw, f, ensure_ascii=False, indent=2)
        
    return doc_id, ocr_results_dir, page_results, combined_raw
