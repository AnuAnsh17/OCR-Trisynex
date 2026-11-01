# Backward-compatible proxy to backend.services.ocr_service
from backend.services.ocr_service import (
    MODEL_REPO,
    get_indic_ocr_parser,
    rasterize_pdf,
    process_page_images,
    prepare_sources,
    process_document_ocr,
)

__all__ = [
    "MODEL_REPO",
    "get_indic_ocr_parser",
    "rasterize_pdf",
    "process_page_images",
    "prepare_sources",
    "process_document_ocr",
]
