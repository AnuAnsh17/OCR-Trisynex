import re
import datetime
from typing import Dict, Any, List, Optional, Tuple
from bs4 import BeautifulSoup

from backend.models import (
    UrjaBillSchema, DocumentMeta, ProviderInfo, BillInfo, CustomerInfo,
    ConnectionInfo, MeterInfo, BillingSummary, ChargesBreakdown,
    ConsumptionInfo, ConsumptionHistoryItem, PaymentInfo, TariffInfo,
    TariffSlab, SecurityDepositInfo, EvidenceItem
)


# Helper regexes and utility functions
NUMBER_CLEAN_RE = re.compile(r"[^\d\.\-]")
DATE_RE = re.compile(r"(\d{1,2}[\/\-\.\s](?:[A-Za-z]{3}|\d{1,2})[\/\-\.\s]\d{2,4})")


def clean_num_str(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    # Handle currency symbols, units like KWH, kW, etc.
    s = s.replace(",", "")
    # Find numeric float pattern
    match = re.search(r"[\-+]?\d+(?:\.\d+)?", s)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None


def clean_text_val(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    # Remove leading colons or bullets
    s = re.sub(r"^[\s:\-\.]+", "", s).strip()
    # Remove footnote markers like $^6$ or numbers at end of label
    s = re.sub(r"\$\^\d+\$", "", s).strip()
    return s if s else None


def extract_key_values_from_html_table(table_html: str) -> List[Tuple[str, str, str]]:
    """
    Parses HTML table and extracts key-value pairs or text cells.
    Returns list of (key, val, raw_cell_pair_str)
    """
    soup = BeautifulSoup(table_html, "html.parser")
    pairs = []
    
    rows = soup.find_all("tr")
    for row in rows:
        cells = [c.get_text(separator=" ", strip=True) for c in row.find_all(["td", "th"])]
        if not cells:
            continue
            
        # Case 1: 2-cell key-value
        if len(cells) == 2:
            pairs.append((cells[0], cells[1], f"{cells[0]} : {cells[1]}"))
        # Case 2: 4-cell key-value (Key1, Val1, Key2, Val2)
        elif len(cells) == 4:
            pairs.append((cells[0], cells[1], f"{cells[0]} : {cells[1]}"))
            pairs.append((cells[2], cells[3], f"{cells[2]} : {cells[3]}"))
        # Case 3: 3-cell where cell 1 might have label and cell 2 has colon + val
        elif len(cells) == 3:
            pairs.append((cells[0], cells[1] + " " + cells[2], f"{cells[0]} : {cells[1]} {cells[2]}"))
            
    return pairs


def extract_key_values_from_text_block(text: str) -> List[Tuple[str, str, str]]:
    """
    Parses plain text block into key-value pairs based on ':' or tab or multi-space delimiters.
    """
    pairs = []
    lines = text.split("\n")
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        if ":" in line_clean:
            parts = line_clean.split(":", 1)
            pairs.append((parts[0].strip(), parts[1].strip(), line_clean))
        elif "\t" in line_clean:
            parts = line_clean.split("\t", 1)
            pairs.append((parts[0].strip(), parts[1].strip(), line_clean))
    return pairs


class UrjaExtractor:
    def __init__(self):
        # Multilingual Field Mapping Dictionary
        self.field_mappings = {
            "account_number": [
                "account no", "account number", "consumer no", "consumer number", "account id",
                "अकाउंट सं.", "ग्राहक क्रमांक", "ग्राहक संख्या", "उपभोक्ता संख्या", "खाते क्रमांक",
                "खाता संख्या", "consumer id", "ca number", "k no"
            ],
            "bill_number": [
                "bill no", "bill number", "बिल संख्या", "देयक क्रमांक", "बिल क्रमांक", "देयक क्र."
            ],
            "bill_date": [
                "bill date", "बिल तिथि", "देयक दिनांक", "बिल दिनांक", "देयक तारीख"
            ],
            "due_date": [
                "due date", "देय तिथि", "देय दिनांक", "नियत तारीख", "भरणा मुदत", "देयक भरणा अंतिम तारीख"
            ],
            "disconnection_date": [
                "disconnection date", "विच्छेदन तिथि", "विच्छेदन दिनांक", "मुदतवाढ दिनांक"
            ],
            "bill_month": [
                "bill month", "बिल माह", "देयक महिना", "बिल महिना"
            ],
            "bill_basis": [
                "bill basis", "बिल आधार", "देयक आधार"
            ],
            "net_billed_unit": [
                "net billed unit", "net billed units", "units consumed", "एकूण वापर", "कुल खपत",
                "एकूण युनिट", "वापर युनिट"
            ],
            "customer_name": [
                "name", "customer name", "consumer name", "नाम", "नाव", "ग्राहकाचे नाव", "उपभोक्ता का नाम"
            ],
            "father_husband_name": [
                "father / husband name", "father name", "पिता/पति का नाम", "वडिलांचे नाव"
            ],
            "address": [
                "address", "पता", "पत्ता", "ग्राहकाचा पत्ता"
            ],
            "mobile": [
                "registered mobile no", "mobile", "mobile no", "पंजीकृत मोबाइल न०", "मोबाईल नंबर"
            ],
            "email": [
                "email", "email id", "ई-मेल"
            ],
            "sanctioned_load": [
                "sanction load", "sanctioned load", "स्वीकृत भार", "मंजूर भार", "स्वीकृत लोड"
            ],
            "billed_demand": [
                "billed demand", "बिल्ड डिमांड", "आकारित भार", "डिमांड"
            ],
            "category": [
                "category", "केटेगरी", "ग्राहकाचा वर्ग", "श्रेणी", "tariff category"
            ],
            "tariff_code": [
                "tariff", "tariff code", "टॅरिफ", "दर पत्रक"
            ],
            "connection_type": [
                "connection type", "संयोजन प्रकार", "जोडणी प्रकार"
            ],
            "connection_date": [
                "connection date", "संयोजन तिथि", "जोडणी दिनांक"
            ],
            "supply_type": [
                "supply type", "सप्लाई टाइप", "पुरवठा प्रकार"
            ],
            "meter_number": [
                "meter number", "meter no", "मीटर संख्या", "मीटर नंबर", "मिटर क्रमांक", "मीटर क्र."
            ],
            "security_deposit": [
                "security deposit", "जमा प्रतिभूति", "सुरक्षा ठेव", "देय प्रतिभूति"
            ],
            "division": [
                "division", "खंड", "विभाग"
            ],
            "subdivision": [
                "subdivision", "उपखंड", "उपविभाग"
            ],
            "billing_unit": [
                "billing unit", "bu", "बिलिंग युनिट", "बिलिंग युनिट क्र."
            ],
            "energy_charges": [
                "energy charges", "ऊर्जा प्रभार", "वीज आकार"
            ],
            "demand_charges": [
                "demand charges", "fixed charges", "मांग प्रभार", "स्थिर आकार", "फिक्सड/मांग प्रभार"
            ],
            "electricity_duty": [
                "electricity duty", "विद्युत कर", "वीज शुल्क"
            ],
            "fuel_adjustment": [
                "fppa surcharge", "fuel adjustment", "ईंधन अधिभार", "इंधन समायोजन आकार", "fppa"
            ],
            "current_lpsc": [
                "current lpsc", "late payment surcharge", "वर्तमान विलम्ब भुगतान अधिभार", "विलंब आकार"
            ],
            "current_bill_amount": [
                "current bill amount", "current bill", "वर्तमान बिल राशि", "चालू देयक", "चालू बिल रक्कम"
            ],
            "arrear_amount": [
                "arrear amount", "arrears", "previous dues", "बकाया धनराशि", "मागील थकबाकी"
            ],
            "payable_amount": [
                "payable amount", "total payable", "कुल देय राशि", "एकूण देयक रक्कम", "देय रक्कम"
            ],
            "due_date_rebate": [
                "due date rebate", "देय तिथि तक छूट", "मुदतीत सवलत"
            ]
        }

    def _normalize_key(self, raw_key: str) -> Optional[str]:
        raw_clean = raw_key.lower().strip()
        # Remove numbers and special characters for matching
        raw_clean = re.sub(r"[\/\\\(\)\:\-\.\_\d\$\^]+", " ", raw_clean).strip()
        
        for std_key, synonyms in self.field_mappings.items():
            for syn in synonyms:
                if syn in raw_clean:
                    return std_key
        return None

    def extract(self, doc_id: str, source_filename: str, ocr_raw_data: Dict[str, Any]) -> UrjaBillSchema:
        pages_raw = ocr_raw_data.get("pages", [])
        if not pages_raw and isinstance(ocr_raw_data, dict):
            # Check if ocr_raw_data maps "page_1.png" -> dict
            pages_list = []
            for idx, (k, v) in enumerate(ocr_raw_data.items(), start=1):
                if isinstance(v, dict) and "blocks" in v:
                    pages_list.append({
                        "page_number": idx,
                        "source_file": k,
                        "result": v
                    })
            pages = pages_list
        else:
            pages = pages_raw
            
        page_count = len(pages)
        
        schema = UrjaBillSchema(
            document=DocumentMeta(
                document_id=doc_id,
                source_filename=source_filename,
                page_count=page_count,
                processed_at=datetime.datetime.now().isoformat()
            )
        )

        evidence_list: List[EvidenceItem] = []
        raw_kv_map: Dict[str, Tuple[Any, int, str, float, List[float]]] = {}

        # ----------------------------------------------------
        # Pass 1: Parse all blocks and gather key-values & tables
        # ----------------------------------------------------
        for page_data in pages:
            page_num = page_data.get("page_number", 1)
            result = page_data.get("result", {})
            blocks = result.get("blocks", [])

            for block in blocks:
                text = block.get("text", "")
                conf = block.get("conf", 0.0)
                bbox = block.get("bbox_xyxy", [])
                block_type = block.get("type", "")

                # Check Provider hints from text headers
                if not schema.provider.name:
                    if "Purvanchal Vidyut" in text or "पूर्वांचल विद्युत" in text or "UPPCL" in text:
                        schema.provider.name = "Purvanchal Vidyut Vitaran Nigam Ltd. (UPPCL)"
                        schema.provider.short_name = "PUVVNL / UPPCL"
                        schema.provider.state = "Uttar Pradesh"
                        schema.provider.website = "www.uppcl.org"
                    elif "MSEDCL" in text or "Mahavitaran" in text or "महावितरण" in text or "महाराष्ट्र राज्य विद्युत" in text:
                        schema.provider.name = "Maharashtra State Electricity Distribution Co. Ltd."
                        schema.provider.short_name = "MSEDCL"
                        schema.provider.state = "Maharashtra"
                        schema.provider.website = "www.mahadiscom.in"

                # Parse key-values if block contains HTML table
                if "<table" in text.lower():
                    pairs = extract_key_values_from_html_table(text)
                    for k_raw, v_raw, line_raw in pairs:
                        norm_k = self._normalize_key(k_raw)
                        v_clean = clean_text_val(v_raw)
                        if norm_k and v_clean and norm_k not in raw_kv_map:
                            raw_kv_map[norm_k] = (v_clean, page_num, line_raw, conf, bbox)
                            
                    # Parse Specific Structured Tables (Meter Details, Tariff Slabs, Consumption History, Last Payment)
                    self._parse_structured_tables(text, page_num, schema, conf, bbox)
                else:
                    pairs = extract_key_values_from_text_block(text)
                    for k_raw, v_raw, line_raw in pairs:
                        norm_k = self._normalize_key(k_raw)
                        v_clean = clean_text_val(v_raw)
                        if norm_k and v_clean and norm_k not in raw_kv_map:
                            raw_kv_map[norm_k] = (v_clean, page_num, line_raw, conf, bbox)
                            
                # Also check inline text patterns like Bill Duration
                if "Bill Duration" in text or "बिल अवधि" in text:
                    dur_match = re.search(r"(\d{1,2}\-[A-Za-z]{3}\-\d{4})\s+[To|to|TO\-]+\s+(\d{1,2}\-[A-Za-z]{3}\-\d{4})", text)
                    if dur_match:
                        schema.bill.billing_period_start = dur_match.group(1)
                        schema.bill.billing_period_end = dur_match.group(2)
                        evidence_list.append(EvidenceItem(
                            field="bill.billing_period",
                            value=f"{dur_match.group(1)} to {dur_match.group(2)}",
                            page=page_num,
                            source_text=text,
                            confidence=conf,
                            bbox=bbox
                        ))

        # ----------------------------------------------------
        # Pass 2: Populate Urja Schema fields from extracted key-values
        # ----------------------------------------------------

        # Account / Consumer Number
        if "account_number" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["account_number"]
            schema.bill.account_number = val
            schema.bill.consumer_number = val
            evidence_list.append(EvidenceItem(
                field="bill.account_number", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        # Bill Number
        if "bill_number" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["bill_number"]
            schema.bill.bill_number = val
            evidence_list.append(EvidenceItem(
                field="bill.bill_number", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        # Bill Month
        if "bill_month" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["bill_month"]
            schema.bill.bill_month = val
            evidence_list.append(EvidenceItem(
                field="bill.bill_month", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        # Dates
        if "bill_date" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["bill_date"]
            schema.bill.bill_date = val
            evidence_list.append(EvidenceItem(
                field="bill.bill_date", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "due_date" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["due_date"]
            schema.bill.due_date = val
            evidence_list.append(EvidenceItem(
                field="bill.due_date", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "disconnection_date" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["disconnection_date"]
            schema.bill.disconnection_date = val
            evidence_list.append(EvidenceItem(
                field="bill.disconnection_date", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "bill_basis" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["bill_basis"]
            schema.bill.bill_basis = val
            evidence_list.append(EvidenceItem(
                field="bill.bill_basis", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        # Customer Details
        if "customer_name" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["customer_name"]
            schema.customer.name = val
            evidence_list.append(EvidenceItem(
                field="customer.name", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "address" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["address"]
            schema.customer.address = val
            evidence_list.append(EvidenceItem(
                field="customer.address", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "mobile" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["mobile"]
            schema.customer.mobile = val
            evidence_list.append(EvidenceItem(
                field="customer.mobile", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "email" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["email"]
            schema.customer.email = val
            evidence_list.append(EvidenceItem(
                field="customer.email", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        # Connection Details
        if "sanctioned_load" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["sanctioned_load"]
            schema.connection.sanctioned_load_kw = clean_num_str(val)
            evidence_list.append(EvidenceItem(
                field="connection.sanctioned_load_kw", value=schema.connection.sanctioned_load_kw,
                page=page_num, source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "billed_demand" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["billed_demand"]
            schema.connection.billed_demand_kw = clean_num_str(val)
            evidence_list.append(EvidenceItem(
                field="connection.billed_demand_kw", value=schema.connection.billed_demand_kw,
                page=page_num, source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "category" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["category"]
            schema.connection.category = val
            evidence_list.append(EvidenceItem(
                field="connection.category", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "connection_type" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["connection_type"]
            schema.connection.connection_type = val
            evidence_list.append(EvidenceItem(
                field="connection.connection_type", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "connection_date" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["connection_date"]
            schema.connection.connection_date = val
            evidence_list.append(EvidenceItem(
                field="connection.connection_date", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "division" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["division"]
            schema.connection.division = val
            evidence_list.append(EvidenceItem(
                field="connection.division", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "subdivision" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["subdivision"]
            schema.connection.subdivision = val
            evidence_list.append(EvidenceItem(
                field="connection.subdivision", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        # Meter Number
        if "meter_number" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["meter_number"]
            schema.meter.meter_number = val
            evidence_list.append(EvidenceItem(
                field="meter.meter_number", value=val, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        # Security Deposit
        if "security_deposit" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["security_deposit"]
            amt = clean_num_str(val)
            schema.security_deposit.amount = amt
            schema.billing.security_deposit = amt
            evidence_list.append(EvidenceItem(
                field="security_deposit.amount", value=amt, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        # Net Units Consumed
        if "net_billed_unit" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["net_billed_unit"]
            units = clean_num_str(val)
            schema.meter.units_consumed = units
            schema.consumption.current_units = units
            evidence_list.append(EvidenceItem(
                field="meter.units_consumed", value=units, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        # Charges & Amounts
        if "energy_charges" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["energy_charges"]
            amt = clean_num_str(val)
            schema.charges.energy_charges = amt
            evidence_list.append(EvidenceItem(
                field="charges.energy_charges", value=amt, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "demand_charges" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["demand_charges"]
            amt = clean_num_str(val)
            schema.charges.demand_charges = amt
            schema.charges.fixed_charges = amt
            evidence_list.append(EvidenceItem(
                field="charges.demand_charges", value=amt, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "electricity_duty" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["electricity_duty"]
            amt = clean_num_str(val)
            schema.charges.electricity_duty = amt
            evidence_list.append(EvidenceItem(
                field="charges.electricity_duty", value=amt, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "fuel_adjustment" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["fuel_adjustment"]
            amt = clean_num_str(val)
            schema.charges.fuel_adjustment = amt
            schema.charges.fppa_surcharge = amt
            evidence_list.append(EvidenceItem(
                field="charges.fuel_adjustment", value=amt, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "current_lpsc" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["current_lpsc"]
            amt = clean_num_str(val)
            schema.charges.lpsc = amt
            schema.billing.late_payment_surcharge = amt
            evidence_list.append(EvidenceItem(
                field="charges.lpsc", value=amt, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "current_bill_amount" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["current_bill_amount"]
            amt = clean_num_str(val)
            schema.billing.current_bill_amount = amt
            evidence_list.append(EvidenceItem(
                field="billing.current_bill_amount", value=amt, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "arrear_amount" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["arrear_amount"]
            amt = clean_num_str(val)
            schema.billing.arrears = amt
            schema.billing.previous_dues = amt
            evidence_list.append(EvidenceItem(
                field="billing.arrears", value=amt, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        if "payable_amount" in raw_kv_map:
            val, page_num, src_text, conf, bbox = raw_kv_map["payable_amount"]
            amt = clean_num_str(val)
            schema.billing.payable_amount = amt
            evidence_list.append(EvidenceItem(
                field="billing.payable_amount", value=amt, page=page_num,
                source_text=src_text, confidence=conf, bbox=bbox
            ))

        schema.evidence = evidence_list
        return schema

    def _parse_structured_tables(self, table_html: str, page_num: int, schema: UrjaBillSchema, conf: float, bbox: List[float]):
        soup = BeautifulSoup(table_html, "html.parser")
        rows = soup.find_all("tr")
        if not rows:
            return

        table_text = soup.get_text()

        # 1. Meter Reading Table Parsing
        if "Meter Number" in table_text or "मीटर संख्या" in table_text or "Meter Reading Details" in table_text:
            for row in rows:
                cells = [c.get_text(separator=" ", strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) >= 5 and any(kwh in cell.upper() for kwh in ["KWH", "UNITS", "KVAH"] for cell in cells):
                    # Find dates in row cells
                    dates = [x for x in cells if DATE_RE.search(x)]
                    # Extract numeric readings from cells excluding column 0 (meter number)
                    readings = []
                    for cell in cells[1:]:
                        num = clean_num_str(cell)
                        # Filter out very long meter numbers or dates
                        if num is not None and not DATE_RE.search(cell) and len(str(int(num))) < 7:
                            readings.append(num)
                            
                    if len(dates) >= 2:
                        schema.meter.previous_reading_date = dates[0]
                        schema.meter.current_reading_date = dates[1]
                    if len(readings) >= 3:
                        schema.meter.previous_reading = readings[0]
                        schema.meter.current_reading = readings[1]
                        schema.meter.meter_reading_difference = readings[2]
                        if schema.meter.units_consumed is None:
                            schema.meter.units_consumed = readings[2]
                        schema.meter.meter_multiplier = 1.0

        # 2. Tariff Slab Table Parsing
        if "Slab" in table_text or "स्लैब" in table_text or "Calculation Details" in table_text:
            for row in rows:
                cells = [c.get_text(separator=" ", strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) >= 4 and ("0-100" in cells[1] or "101-150" in cells[1] or "151-300" in cells[1] or "Above" in cells[1]):
                    slab_range = cells[1]
                    units = clean_num_str(cells[2])
                    # Parse rates or amount if available
                    rate = None
                    amt = None
                    if len(cells) >= 5:
                        amt = clean_num_str(cells[4])
                    slab = TariffSlab(
                        from_unit=clean_num_str(slab_range.split("-")[0]) if "-" in slab_range else None,
                        to_unit=clean_num_str(slab_range.split("-")[1]) if "-" in slab_range else None,
                        units=units,
                        rate=rate,
                        amount=amt
                    )
                    schema.tariff.slabs.append(slab)

        # 3. Consumption History Table Parsing
        if "Last Six month" in table_text or "विगत छ: माह का उपभोग" in table_text or "Consumption" in table_text:
            for row in rows:
                cells = [c.get_text(separator=" ", strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) >= 4:
                    month_str = cells[1]
                    demand_val = clean_num_str(cells[2])
                    units_val = clean_num_str(cells[3])
                    if units_val is not None and ("202" in month_str or "AUG" in month_str or "JUL" in month_str or "JUN" in month_str or "MAY" in month_str or "APR" in month_str or "MAR" in month_str):
                        schema.consumption.consumption_history.append(
                            ConsumptionHistoryItem(
                                period=month_str,
                                units=units_val,
                                demand_kw=demand_val
                            )
                        )

        # 4. Last Payment Details Table Parsing
        if "Last Payment" in table_text or "अंतिम भुगतान" in table_text:
            for row in rows:
                cells = [c.get_text(separator=" ", strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) == 4 and DATE_RE.search(cells[0]):
                    schema.payment.last_payment_date = cells[0]
                    schema.payment.last_payment_amount = clean_num_str(cells[1])
                    schema.payment.last_payment_mode = cells[2]
                    schema.payment.last_receipt_number = cells[3]
