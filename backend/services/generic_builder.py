import re
import datetime
from typing import Dict, Any, List, Optional, Tuple
from bs4 import BeautifulSoup

from backend.models.generic import (
    GenericDocument, GenericDocumentMeta, DocumentProcessingInfo,
    PageData, GenericTable, GenericField, GenericSection,
    GenericVisualElement, GenericSourceInfo
)
from backend.services.classifier import classify_document_type


def parse_html_table(table_html: str, page_num: int, table_idx: int, conf: float, bbox: List[float]) -> Tuple[GenericTable, List[GenericField]]:
    soup = BeautifulSoup(table_html, "html.parser")
    table_id = f"table_p{page_num}_{table_idx}"
    
    # Extract title if present in caption or th
    title = None
    caption = soup.find("caption")
    if caption:
        title = caption.get_text(strip=True)
        
    headers = []
    rows = []
    structured_cells = []
    fields = []
    thead = soup.find("thead")
    if thead:
        for tr in thead.find_all("tr"):
            ths = tr.find_all(["th", "td"], recursive=False)
            if len(ths) == 1 and (ths[0].get("colspan") or "Table" in ths[0].get_text()):
                title = title or ths[0].get_text(separator=" ", strip=True)
    # Extract header rows if present
    if thead:
        for tr in thead.find_all("tr"):
            th_cells = [th.get_text(separator=" ", strip=True) for th in tr.find_all(["th", "td"])]
            if th_cells:
                if not title and len(th_cells) == 1 and "Table" in th_cells[0]:
                    title = th_cells[0]
                else:
                    headers.append(th_cells)
                    
    tbody = soup.find("tbody") or soup
    active_spans = {}
    for tr_idx, tr in enumerate(tbody.find_all("tr")):
        cells = [td.get_text(separator=" ", strip=True) for td in tr.find_all(["td", "th"])]
        if not cells:
            continue
            
        # Keep spanning title rows in raw_html, but don't repeat them as data rows.
        row_cells = tr.find_all(["td", "th"], recursive=False)
        for col_idx, cell in enumerate(row_cells):
            structured_cells.append({"row": tr_idx, "column": col_idx, "text": cell.get_text(separator=" ", strip=True), "bbox": None, "confidence": None, "rowspan": int(cell.get("rowspan", 1)), "colspan": int(cell.get("colspan", 1))})
        if len(row_cells) == 1 and (row_cells[0].get("colspan") or "Table" in cells[0]):
            if not title:
                title = cells[0]
            continue
        if len(cells) == 1:
            lines = [line.strip() for line in row_cells[0].stripped_strings if line.strip()]
            active_label = None
            for line in lines:
                if re.search(r"[A-Za-z\u0900-\u097F]", line) and not re.fullmatch(r"[\d,]+(?:\.\d+)?", line):
                    active_label = line
                elif active_label and re.fullmatch(r"[\d,]+(?:\.\d+)?", line):
                    fields.append(GenericField(field_id=f"field_p{page_num}_t{table_idx}_r{tr_idx}_{len(fields)}", label=active_label, value=line, normalized_value=line, page=page_num, confidence=conf, source=GenericSourceInfo(text=f"{active_label}: {line}", page=page_num, confidence=conf, bbox=bbox)))
                    active_label = None
        
        # Expand merged body cells into a rectangular view for the generic renderer.
        grid_row, next_spans, col_idx = [], {}, 0
        for cell in row_cells:
            while col_idx in active_spans:
                text_value, remaining = active_spans[col_idx]
                grid_row.append(text_value)
                if remaining > 1: next_spans[col_idx] = (text_value, remaining - 1)
                col_idx += 1
            text_value = cell.get_text(separator=" ", strip=True)
            colspan = int(cell.get("colspan", 1)); rowspan = int(cell.get("rowspan", 1))
            for offset in range(colspan):
                grid_row.append(text_value if offset == 0 else "")
                if rowspan > 1: next_spans[col_idx + offset] = (text_value if offset == 0 else "", rowspan - 1)
            col_idx += colspan
        while col_idx in active_spans:
            text_value, remaining = active_spans[col_idx]
            grid_row.append(text_value)
            if remaining > 1: next_spans[col_idx] = (text_value, remaining - 1)
            col_idx += 1
        active_spans = next_spans
        rows.append(grid_row or cells)
        
        # Extract generic label/value pairs from even-width rows, while retaining
        # the original cells and HTML exactly for all other table structures.
        if len(cells) >= 2 and len(cells) % 2 == 0:
            for c_idx in range(0, len(cells), 2):
                label, val = cells[c_idx], cells[c_idx + 1]
                if label and val and len(label) < 100:
                    fields.append(GenericField(
                        field_id=f"field_p{page_num}_t{table_idx}_r{tr_idx}_{c_idx}",
                        label=label,
                        value=val,
                        normalized_value=val.strip(": "),
                        page=page_num,
                        confidence=conf,
                        source=GenericSourceInfo(text=f"{label} : {val}", page=page_num, confidence=conf, bbox=bbox)
                    ))
                    
    # Flatten column list for generic representation
    flat_cols = []
    if headers:
        flat_cols = headers[-1]
    elif rows and len(rows[0]) > 0:
        flat_cols = [f"Col {i+1}" for i in range(len(rows[0]))]

    # Table structures and merged cells stay lossless in raw_html; derive a title
    # from the first spanning header if IndicOCR marks the title row with colspan.
    if not title:
        first_row = soup.find("tr")
        if first_row:
            first_cells = first_row.find_all(["th", "td"], recursive=False)
            if len(first_cells) == 1 and first_cells[0].get("colspan"):
                title = first_cells[0].get_text(separator=" ", strip=True)

    gen_table = GenericTable(
        table_id=table_id,
        title=title or f"Table {table_idx} (Page {page_num})",
        columns=flat_cols,
        rows=rows,
        headers=[c for h in headers for c in h],
        page=page_num,
        confidence=conf,
        bbox=bbox,
        raw_html=table_html,
        raw_table=table_html
        ,cells=structured_cells,
        header_rows=headers
    )
    
    return gen_table, fields


class GenericDocumentBuilder:
    def build(self, doc_id: str, filename: str, ocr_raw_data: Dict[str, Any]) -> GenericDocument:
        pages_raw = ocr_raw_data.get("pages", [])
        if not pages_raw and isinstance(ocr_raw_data, dict):
            pages_list = []
            for idx, (k, v) in enumerate(ocr_raw_data.items(), start=1):
                if isinstance(v, dict) and "blocks" in v:
                    pages_list.append({"page_number": idx, "source_file": k, "result": v})
            pages_input = pages_list
        else:
            pages_input = pages_raw

        all_page_objects: List[PageData] = []
        all_doc_fields: List[GenericField] = []
        all_doc_tables: List[GenericTable] = []
        all_doc_sections: List[GenericSection] = []
        all_doc_visuals: List[GenericVisualElement] = []
        unmapped_blocks: List[Dict[str, Any]] = []

        full_doc_text_parts = []
        detected_languages = set()

        for page_num, page_item in enumerate(pages_input, start=1):
            result = page_item.get("result") or {}
            blocks = result.get("blocks", [])
            if page_item.get("status") == "failed":
                blocks = [{"label": "OCRFailure", "type": "Error", "text": page_item.get("error", "OCR failed"), "order": 0, "bbox_xyxy": None, "conf": None}]
            width = result.get("width")
            height = result.get("height")

            page_text_parts = []
            page_tables: List[GenericTable] = []
            page_fields: List[GenericField] = []
            page_sections: List[GenericSection] = []
            page_visuals: List[GenericVisualElement] = []

            table_counter = 1
            section_counter = 1
            visual_counter = 1

            for b_idx, block in enumerate(blocks):
                label = block.get("label", "")
                b_type = block.get("type", "")
                text = block.get("text", "")
                conf = block.get("conf", 0.0)
                bbox = block.get("bbox_xyxy", [])

                if text:
                    page_text_parts.append(text)
                    full_doc_text_parts.append(text)

                # Check languages in text
                if re.search(r"[\u0900-\u097F]", text):
                    detected_languages.add("hi/mr (Devanagari)")
                if re.search(r"[a-zA-Z]", text):
                    detected_languages.add("en (English)")

                # Process Tables
                if "<table" in text.lower() or b_type == "Table" or label == "Table":
                    if "<table" in text.lower():
                        g_table, g_fields = parse_html_table(text, page_num, table_counter, conf, bbox)
                        page_tables.append(g_table)
                        all_doc_tables.append(g_table)
                        page_fields.extend(g_fields)
                        all_doc_fields.extend(g_fields)
                        table_counter += 1
                    else:
                        # Keep non-HTML table payloads available as generic rows and raw blocks.
                        unmapped_blocks.append(block)
                        raw_rows = block.get("rows") or block.get("cells")
                        if isinstance(raw_rows, list):
                            table_rows = [row if isinstance(row, list) else [row] for row in raw_rows]
                            table = GenericTable(table_id=f"table_p{page_num}_{table_counter}", title=label or f"Table {table_counter}", rows=table_rows, page=page_num, confidence=conf, bbox=bbox)
                            page_tables.append(table)
                            all_doc_tables.append(table)
                            table_counter += 1

                # Retain every non-table block as a section too; typed views are conveniences.
                if "<table" not in text.lower() and b_type != "Table" and label != "Table" and text.strip() and not (b_type in ["Figure", "PageHeader", "PageFooter"] or label in ["Diagram", "Header", "Footer", "Logo"] or "qr" in str(label).lower() or "qr" in str(b_type).lower() or "barcode" in str(label).lower()):
                    sec = GenericSection(section_id=f"sec_p{page_num}_block{b_idx}", title=(text.strip().splitlines()[0][:180] or label or b_type), type=(label or b_type or "text").lower().replace(" ", "_"), page=page_num, content=text, bullets=[line.strip() for line in text.splitlines() if line.strip()], confidence=conf, bbox=bbox)
                    page_sections.append(sec)
                    all_doc_sections.append(sec)

                # Process Visual Elements (Figure, Diagram, QR code, Logo, Barcode)
                if b_type in ["Figure", "PageHeader", "PageFooter"] or label in ["Diagram", "Header", "Footer", "Logo"] or "qr" in str(label).lower() or "qr" in str(b_type).lower() or "barcode" in str(label).lower():
                    vis_type = "qr_code" if "qr" in str(label).lower() or "qr" in str(b_type).lower() else (b_type or label or "figure")
                    vis_elem = GenericVisualElement(
                        element_id=f"vis_p{page_num}_{visual_counter}",
                        type=vis_type,
                        page=page_num,
                        bbox=bbox,
                        confidence=conf,
                        text=text
                    )
                    page_visuals.append(vis_elem)
                    all_doc_visuals.append(vis_elem)
                    visual_counter += 1

                # Process Sections (SectionHeader, Notes, Legal Notices, List, Contact-info)
                elif label in ["Section-title", "List", "Contact-info", "Infobox"] or b_type in ["SectionHeader", "Caption", "Text"]:
                    if any(kw in text for kw in ["à¤Ÿà¤¿à¤ªà¥à¤ªà¤£à¤¿à¤¯à¤¾à¤", "Notes", "à¤§à¥à¤¯à¤¾à¤¨ à¤¦à¥‡à¤‚", "à¤µà¤¿à¤•à¤²à¥à¤ª", "Notice", "à¤¨à¥‹à¤Ÿ", "Instructions"]):
                        bullets = [line.strip() for line in text.split("\n") if line.strip()]
                        sec = GenericSection(
                            section_id=f"sec_p{page_num}_{section_counter}",
                            title=bullets[0] if bullets else "Notes / Instructions",
                            type="legal_notice" if "Notice" in text else "notes",
                            page=page_num,
                            content=text,
                            bullets=bullets,
                            confidence=conf,
                            bbox=bbox
                        )
                        if not any(existing.content == text for existing in page_sections):
                            page_sections.append(sec)
                            all_doc_sections.append(sec)
                        section_counter += 1
                    else:
                        # Extract key values from plain text lines
                        lines = text.split("\n")
                        for l_idx, line in enumerate(lines):
                            if ":" in line:
                                parts = line.split(":", 1)
                                k_str = parts[0].strip()
                                v_str = parts[1].strip()
                                if k_str and v_str:
                                    g_field = GenericField(
                                        field_id=f"field_p{page_num}_b{b_idx}_l{l_idx}",
                                        label=k_str,
                                        value=v_str,
                                        normalized_value=v_str,
                                        page=page_num,
                                        confidence=conf,
                                        source=GenericSourceInfo(text=line, page=page_num, confidence=conf, bbox=bbox)
                                    )
                                    page_fields.append(g_field)
                                    all_doc_fields.append(g_field)

            page_obj = PageData(
                page_number=page_num,
                page_order=page_item.get("page_order", page_num),
                source_id=page_item.get("source_id"),
                source_filename=page_item.get("source_filename"),
                image_path=page_item.get("image_path"),
                status=page_item.get("status", "completed"),
                width=width,
                height=height,
                full_text="\n\n".join(page_text_parts),
                blocks=blocks,
                tables=page_tables,
                fields=page_fields,
                sections=page_sections,
                visual_elements=page_visuals
            )
            all_page_objects.append(page_obj)

        full_doc_text = "\n\n".join(full_doc_text_parts)
        doc_type, doc_conf = classify_document_type(full_doc_text)

        doc_meta = GenericDocumentMeta(
            id=doc_id,
            filename=filename,
            page_count=len(pages_input),
            document_type=doc_type,
            document_type_confidence=doc_conf,
            languages=list(detected_languages),
            ocr_metadata={k: v for k, v in ocr_raw_data.items() if k != "pages"},
            processing=DocumentProcessingInfo(
                ocr_engine="IndicOCR",
                ocr_model="bodhan-ai/indic-ocr",
                processed_at=datetime.datetime.now().isoformat()
            )
        )

        return GenericDocument(
            document=doc_meta,
            pages=all_page_objects,
            fields=all_doc_fields,
            tables=all_doc_tables,
            sections=all_doc_sections,
            visual_elements=all_doc_visuals,
            unmapped_blocks=unmapped_blocks,
            additional_fields=all_doc_fields,
            additional_tables=all_doc_tables,
            additional_sections=all_doc_sections,
            additional_elements=all_doc_visuals,
            raw_ocr=ocr_raw_data
        )






