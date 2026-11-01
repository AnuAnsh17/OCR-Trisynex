from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentProcessingInfo(BaseModel):
    ocr_engine: str = "IndicOCR"
    ocr_model: str = "bodhan-ai/indic-ocr"
    processed_at: str


class GenericDocumentMeta(BaseModel):
    id: str
    filename: str
    page_count: int
    document_type: str = "unknown"
    document_type_confidence: float = 1.0
    languages: List[str] = Field(default_factory=list)
    processing: DocumentProcessingInfo
    ocr_metadata: Dict[str, Any] = Field(default_factory=dict)


class GenericSourceInfo(BaseModel):
    text: str
    page: int
    confidence: Optional[float] = None
    bbox: Optional[List[float]] = None
    source_block_id: Optional[int] = None


class GenericField(BaseModel):
    field_id: str
    label: str
    value: Any
    normalized_value: Optional[Any] = None
    value_type: str = "string"  # string, number, date, boolean
    page: int
    confidence: Optional[float] = None
    source: GenericSourceInfo


class GenericTable(BaseModel):
    table_id: str
    title: Optional[str] = None
    columns: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)
    headers: List[str] = Field(default_factory=list)
    page: int
    confidence: Optional[float] = None
    bbox: Optional[List[float]] = None
    raw_html: Optional[str] = None
    raw_table: Optional[str] = None
    cells: List[Dict[str, Any]] = Field(default_factory=list)
    header_rows: List[List[str]] = Field(default_factory=list)
    source_block_id: Optional[int] = None


class GenericSection(BaseModel):
    section_id: str
    title: str
    type: str  # legal_notice, notes, instructions, contact_info, payment_options, summary
    page: int
    content: str
    bullets: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    bbox: Optional[List[float]] = None


class GenericVisualElement(BaseModel):
    element_id: str
    type: str  # figure, qr_code, barcode, logo, diagram, signature
    page: int
    bbox: Optional[List[float]] = None
    confidence: Optional[float] = None
    text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PageData(BaseModel):
    page_number: int
    page_order: Optional[int] = None
    source_id: Optional[str] = None
    source_filename: Optional[str] = None
    image_path: Optional[str] = None
    status: str = "completed"
    width: Optional[int] = None
    height: Optional[int] = None
    full_text: str = ""
    blocks: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[GenericTable] = Field(default_factory=list)
    fields: List[GenericField] = Field(default_factory=list)
    sections: List[GenericSection] = Field(default_factory=list)
    visual_elements: List[GenericVisualElement] = Field(default_factory=list)


class GenericDocument(BaseModel):
    document: GenericDocumentMeta
    pages: List[PageData] = Field(default_factory=list)
    fields: List[GenericField] = Field(default_factory=list)
    tables: List[GenericTable] = Field(default_factory=list)
    sections: List[GenericSection] = Field(default_factory=list)
    visual_elements: List[GenericVisualElement] = Field(default_factory=list)
    unmapped_blocks: List[Dict[str, Any]] = Field(default_factory=list)
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    additional_fields: List[GenericField] = Field(default_factory=list)
    additional_tables: List[GenericTable] = Field(default_factory=list)
    additional_sections: List[GenericSection] = Field(default_factory=list)
    additional_elements: List[GenericVisualElement] = Field(default_factory=list)
    # Exact provider payload retained alongside the normalized convenience views.
    raw_ocr: Dict[str, Any] = Field(default_factory=dict)


