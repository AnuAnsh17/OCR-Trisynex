import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

from backend.models.generic import GenericDocument, GenericTable, GenericField
from backend.models.semantic import (
    ElectricityBillSemantic, ProviderInfo, CustomerInfo, AccountInfo,
    BillInfo, ConnectionInfo, MeterInfo, BillMoney, ChargeItem,
    TariffSlab, ConsumptionHistoryItem, SolarNetMetering, PaymentDetails,
    SecurityDepositInfo, EvidenceItem
)


def clean_num(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "")
    match = re.search(r"[\-+]?\d+(?:\.\d+)?", s)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None


class ElectricityBillAdapter:
    def adapt(self, doc: GenericDocument) -> ElectricityBillSemantic:
        semantic = ElectricityBillSemantic(domain="electricity_bill")
        evidence_list: List[EvidenceItem] = []

        # Helper for evidence tracking
        def add_evidence(target_field: str, val: Any, field_obj: Optional[GenericField] = None, table_name: Optional[str] = None, page: Optional[int] = None, source_text: Optional[str] = None, confidence: Optional[float] = None, bbox: Optional[List[float]] = None):
            if val is None or val == "":
                return
            ev = EvidenceItem(
                field=target_field,
                value=val,
                page=field_obj.page if field_obj else (page or 1),
                source_table=table_name,
                source_text=field_obj.source.text if field_obj else (source_text or str(val)),
                confidence=field_obj.confidence if field_obj else (confidence if confidence is not None else 0.9),
                bbox=field_obj.source.bbox if field_obj else bbox
            )
            evidence_list.append(ev)

        # Provider name remains OCR-derived; provider-specific defaults belong nowhere in the generic layer.
        provider_candidates = [str(block.get("text", "")).strip() for page in doc.pages for block in page.blocks if block.get("text")]
        for candidate in provider_candidates:
            first_line = candidate.splitlines()[0].strip()
            if "electricity" in first_line.lower() or "vidyut" in first_line.lower():
                semantic.provider.name = first_line
                add_evidence("provider.name", first_line)
                break

        # 2. Extract Fields from generic fields
        for f_obj in doc.fields:
            lbl = re.sub(r"[^\w\s]", "", f_obj.label.lower()).strip()
            val = str(f_obj.normalized_value if f_obj.normalized_value is not None else f_obj.value).strip().lstrip(": ")

            if "previous dues" in lbl or "arrear amount" in lbl or "बकाया धनराशि" in lbl:
                amount = clean_num(val)
                if amount is not None:
                    semantic.money.previous_dues = amount
                    semantic.money.arrears = amount
                    add_evidence("money.previous_dues", amount, f_obj)
                continue
            
            # Account / Consumer Number
            if any(k in lbl for k in ["account no", "consumer no", "\u0905\u0915\u093e\u0909\u0902\u091f \u0938\u0902", "\u0917\u094d\u0930\u093e\u0939\u0915 \u0915\u094d\u0930\u092e\u093e\u0902\u0915", "\u0916\u093e\u0924\u093e \u0915\u094d\u0930\u092e\u093e\u0902\u0915"]):
                if not semantic.account.account_number:
                    semantic.account.account_number = val
                    semantic.account.consumer_number = val
                    add_evidence("account.account_number", val, f_obj)

            # Bill Number
            elif any(k in lbl for k in ["bill no", "\u092c\u093f\u0932 \u0938\u0902\u0916\u094d\u092f\u093e", "\u092c\u093f\u0932 \u0915\u094d\u0930\u092e\u093e\u0902\u0915"]):
                if not semantic.account.bill_number:
                    semantic.account.bill_number = val
                    add_evidence("account.bill_number", val, f_obj)

            # Bill Date
            elif any(k in lbl for k in ["bill date", "\u092c\u093f\u0932 \u0924\u093f\u0925\u093f", "\u092c\u093f\u0932 \u0926\u093f\u0928\u093e\u0902\u0915"]):
                if not semantic.bill.bill_date:
                    semantic.bill.bill_date = val
                    add_evidence("bill.bill_date", val, f_obj)

            # Due Date
            elif any(k in lbl for k in ["due date", "\u0926\u0947\u092f \u0924\u093f\u0925\u093f", "\u0926\u0947\u092f \u0926\u093f\u0928\u093e\u0902\u0915"]):
                if not semantic.bill.due_date:
                    semantic.bill.due_date = val
                    add_evidence("bill.due_date", val, f_obj)

            # Disconnection Date
            elif any(k in lbl for k in ["disconnection date", "\u0935\u093f\u091a\u094d\u091b\u0947\u0926\u0928 \u0924\u093f\u0925\u093f"]):
                if not semantic.bill.disconnection_date:
                    semantic.bill.disconnection_date = val
                    add_evidence("bill.disconnection_date", val, f_obj)

            # Customer Name
            elif any(k in lbl for k in ["father", "husband", "\u092a\u093f\u0924\u093e", "\u092a\u0924\u093f"]):
                if not semantic.customer.father_husband_name:
                    semantic.customer.father_husband_name = val
                    add_evidence("customer.father_husband_name", val, f_obj)
            elif any(k in lbl for k in ["name", "नाम", "नाव"]):
                if not semantic.customer.name:
                    semantic.customer.name = val
                    add_evidence("customer.name", val, f_obj)

            # Address
            elif any(k in lbl for k in ["address", "\u092a\u0924\u093e", "\u092a\u0924\u094d\u0924\u093e"]):
                if not semantic.customer.address:
                    semantic.customer.address = val
                    add_evidence("customer.address", val, f_obj)

            # Sanctioned Load
            elif any(k in lbl for k in ["sanction load", "\u0938\u094d\u0935\u0940\u0915\u0943\u0924 \u092d\u093e\u0930", "\u092e\u0902\u091c\u0942\u0930 \u092d\u093e\u0930"]):
                if semantic.connection.sanctioned_load_kw is None:
                    semantic.connection.sanctioned_load_kw = clean_num(val)
                    add_evidence("connection.sanctioned_load_kw", semantic.connection.sanctioned_load_kw, f_obj)

            # Billed Demand
            elif any(k in lbl for k in ["billed demand", "\u092c\u093f\u0932\u094d\u0921 \u0921\u093f\u092e\u093e\u0902\u0921", "\u092c\u093f\u0932 \u0915\u0947\u0932\u0947\u0932\u0940 \u092e\u093e\u0917\u0923\u0940"]):
                if semantic.connection.billed_demand_kw is None:
                    semantic.connection.billed_demand_kw = clean_num(val)
                    add_evidence("connection.billed_demand_kw", semantic.connection.billed_demand_kw, f_obj)

            # Meter Number
            elif any(k in lbl for k in ["meter number", "meter no", "\u092e\u0940\u091f\u0930 \u0938\u0902\u0916\u094d\u092f\u093e", "\u092e\u0940\u091f\u0930 \u0915\u094d\u0930\u092e\u093e\u0902\u0915"]):
                if not semantic.meter.meter_number:
                    semantic.meter.meter_number = val
                    add_evidence("meter.meter_number", val, f_obj)

            # Security Deposit
            elif any(k in lbl for k in ["security deposit", "\u091c\u092e\u093e \u092a\u094d\u0930\u0924\u093f\u092d\u0942\u0924\u093f", "\u0905\u0928\u093e\u092e\u0924 \u0930\u0915\u094d\u0915\u092e"]):
                if semantic.money.security_deposit is None:
                    amt = clean_num(val)
                    semantic.money.security_deposit = amt
                    semantic.security_deposit.amount = amt
                    add_evidence("money.security_deposit", amt, f_obj)

            elif "connection date" in lbl and semantic.connection.connection_date is None:
                semantic.connection.connection_date = val
                add_evidence("connection.connection_date", val, f_obj)
            elif "connection type" in lbl and semantic.connection.connection_type is None:
                semantic.connection.connection_type = val
                add_evidence("connection.connection_type", val, f_obj)
            elif "supply type" in lbl and semantic.connection.supply_type is None:
                semantic.connection.supply_type = val
                add_evidence("connection.supply_type", val, f_obj)
            elif "category" in lbl and semantic.connection.category is None:
                semantic.connection.category = val
                add_evidence("connection.category", val, f_obj)
            elif "metering arrangement" in lbl and semantic.connection.metering_arrangement is None:
                semantic.connection.metering_arrangement = val
                add_evidence("connection.metering_arrangement", val, f_obj)
            elif "registered mobile" in lbl or ("mobile" in lbl and semantic.customer.mobile is None):
                semantic.customer.mobile = val
                add_evidence("customer.mobile", val, f_obj)
            elif "email" in lbl and semantic.customer.email is None:
                semantic.customer.email = val
                add_evidence("customer.email", val, f_obj)
            elif "e-kyc" in lbl and semantic.connection.e_kyc is None:
                semantic.connection.e_kyc = val
                add_evidence("connection.e_kyc", val, f_obj)
            elif "printed on" in lbl or "printed date" in lbl:
                if semantic.bill.printed_date is None:
                    semantic.bill.printed_date = val
                    add_evidence("bill.printed_date", val, f_obj)
            elif "bill month" in lbl and semantic.bill.bill_month is None:
                semantic.bill.bill_month = val
                add_evidence("bill.bill_month", val, f_obj)
            elif "bill basis" in lbl and semantic.bill.bill_basis is None:
                semantic.bill.bill_basis = val
                add_evidence("bill.bill_basis", val, f_obj)
            elif "billing duration" in lbl or "bill duration" in lbl or "\u092c\u093f\u0932 \u0905\u0935\u0927\u093f" in lbl or "\u092c\u093f\u0932 \u0915\u093e\u0932\u093e\u0935\u0927\u0940" in lbl:
                dates = re.findall(r"\d{1,2}-[A-Za-z]{3}-\d{4}", val)
                if len(dates) >= 2:
                    semantic.bill.billing_period_start, semantic.bill.billing_period_end = dates[:2]
                    add_evidence("bill.billing_period_start", dates[0], f_obj)
                    add_evidence("bill.billing_period_end", dates[1], f_obj)
            elif "tariff" in lbl and semantic.connection.tariff_description is None:
                semantic.connection.tariff_description = val
                add_evidence("connection.tariff_description", val, f_obj)
            elif "phase" in lbl and semantic.connection.phase is None:
                semantic.connection.phase = val
                add_evidence("connection.phase", val, f_obj)
            elif "voltage" in lbl and semantic.connection.voltage is None:
                semantic.connection.voltage = val
                add_evidence("connection.voltage", val, f_obj)
            elif "feeder" in lbl and semantic.connection.feeder is None:
                semantic.connection.feeder = val
                add_evidence("connection.feeder", val, f_obj)
            elif "pole" in lbl and semantic.connection.pole_number is None:
                semantic.connection.pole_number = val
                add_evidence("connection.pole_number", val, f_obj)
            elif "dtc" in lbl and semantic.connection.dtc_number is None:
                semantic.connection.dtc_number = val
                add_evidence("connection.dtc_number", val, f_obj)
            elif "website" in lbl and semantic.provider.website is None:
                semantic.provider.website = val
                add_evidence("provider.website", val, f_obj)
            elif "portal" in lbl and semantic.provider.customer_portal is None:
                semantic.provider.customer_portal = val
                add_evidence("provider.customer_portal", val, f_obj)
            elif "gstin" in lbl and semantic.provider.gstin is None:
                semantic.provider.gstin = val
                add_evidence("provider.gstin", val, f_obj)
            elif re.search(r"\bcin\b", lbl) and semantic.provider.cin is None:
                semantic.provider.cin = val
                add_evidence("provider.cin", val, f_obj)
            elif "division" in lbl or "\u0916\u0902\u0921" in lbl or "\u0935\u093f\u092d\u093e\u0917" in lbl:
                if semantic.connection.division is None and "sub" not in lbl:
                    semantic.connection.division = val
            elif "subdivision" in lbl or "\u0909\u092a\u0916\u0902\u0921" in lbl or "\u0909\u092a\u0935\u093f\u092d\u093e\u0917" in lbl:
                if semantic.connection.subdivision is None:
                    semantic.connection.subdivision = val

        # 3. Parse First-Class Generic Tables for Domain Concepts
        for table in doc.tables:
            tbl_title = table.title or ""
            tbl_text = tbl_title + " " + " ".join([str(c) for r in table.rows for c in r])

            # The bill header often has a key/value grid without a title. Map only
            # explicitly labeled rows so unrelated numeric cells stay untouched.
            for row in table.rows:
                for index, cell in enumerate(row):
                    label = str(cell).lower()
                    value = str(row[index + 1]).strip().lstrip(": ") if index + 1 < len(row) else ""
                    if value and ("bill no" in label or "बिल संख्या" in label) and semantic.account.bill_number is None:
                        semantic.account.bill_number = value
                        add_evidence("account.bill_number", value, table_name=table.table_id)
                    if value and ("bill date" in label or "बिल तिथि" in label) and semantic.bill.bill_date is None:
                        semantic.bill.bill_date = value
                        add_evidence("bill.bill_date", value, table_name=table.table_id)
                    if value and ("bill month" in label or "बिल माह" in label) and semantic.bill.bill_month is None:
                        semantic.bill.bill_month = value
                        add_evidence("bill.bill_month", value, table_name=table.table_id)

            # Recognize common reading/history/solar structures by row values, independent of table number.
            table_headers = [str(value).casefold() for value in (table.header_rows[-1] if table.header_rows else table.columns)]
            read_cols = [i for i, label in enumerate(table_headers) if "read" in label]
            diff_col = next((i for i, label in enumerate(table_headers) if "diff" in label), 6)
            multiplier_col = next((i for i, label in enumerate(table_headers) if "m.f" in label or "multiplier" in label), 7)
            consumption_col = next((i for i, label in enumerate(table_headers) if "consumption" in label), 8)
            previous_col = read_cols[0] if read_cols else 3
            current_col = read_cols[1] if len(read_cols) > 1 else 5
            for row in table.rows:
                row_text = " ".join(str(cell) for cell in row)
                if len(row) >= 9 and any(unit in row_text.upper() for unit in ("KWH", "KVAH")):
                    dates = [str(cell) for cell in row if re.search(r"\d{1,2}-[A-Za-z]{3}-\d{4}", str(cell))]
                    if len(dates) >= 2:
                        semantic.meter.previous_reading_date = semantic.meter.previous_reading_date or dates[0]
                        semantic.meter.current_reading_date = semantic.meter.current_reading_date or dates[1]
                        positions = [previous_col, current_col, diff_col, multiplier_col, consumption_col]
                        values = [clean_num(row[i]) if i < len(row) else None for i in positions]
                        semantic.meter.previous_reading = semantic.meter.previous_reading or values[0]
                        semantic.meter.current_reading = semantic.meter.current_reading or values[1]
                        semantic.meter.reading_difference = semantic.meter.reading_difference or values[2]
                        semantic.meter.meter_multiplier = semantic.meter.meter_multiplier or values[3]
                        semantic.meter.units_consumed = semantic.meter.units_consumed or values[4]
                        for field_name, value in (("meter.previous_reading", values[0]), ("meter.current_reading", values[1]), ("meter.units_consumed", values[4])):
                            if value is not None:
                                add_evidence(field_name, value, table_name=table.table_id, page=table.page, source_text=" | ".join(str(cell) for cell in row), confidence=table.confidence, bbox=table.bbox)
                if len(row) >= 4 and re.fullmatch(r"[A-Za-z]{3}-\d{4}", str(row[1]).strip()):
                    item = ConsumptionHistoryItem(period=str(row[1]), demand_kw=clean_num(row[2]), units=clean_num(row[3]))
                    semantic.consumption_history.append(item)
                for index in range(0, len(row) - 1, 2):
                    label, amount = str(row[index]).casefold(), clean_num(row[index + 1])
                    if amount is None:
                        continue
                    if "assessed unit" in label: semantic.solar_net_metering.assessed_units = amount
                    elif "opening surplus solar" in label: semantic.solar_net_metering.opening_surplus_units = amount
                    elif "closing surplus solar" in label: semantic.solar_net_metering.closing_surplus_units = amount
                    elif "p2p sold" in label: semantic.solar_net_metering.p2p_sold_units = amount
                    elif "p2p bought" in label: semantic.solar_net_metering.p2p_bought_units = amount

            money_fields = {
                "previous dues": ("money.previous_dues", "previous_dues"), "arrear amount": ("money.previous_dues", "previous_dues"),
                "current bill amount": ("money.current_bill_amount", "current_bill_amount"),
                "payable by due date": ("money.payable_by_due_date", "payable_by_due_date"),
                "due date rebate": ("money.due_date_rebate", "due_date_rebate"),
                "minimum payable amount": ("money.minimum_payable_amount", "minimum_payable_amount"),
                "payable amount": ("money.payable_amount", "payable_amount"),
            }
            for row in table.rows:
                for i, cell in enumerate(row):
                    label_text = str(cell).casefold()
                    for label_key, (evidence_name, attr) in money_fields.items():
                        if label_key not in label_text:
                            continue
                        inline_numbers = re.findall(r"\d[\d,]*(?:\.\d+)?", str(cell))
                        next_value = str(row[i + 1]).strip() if i + 1 < len(row) else ""
                        inline_value = inline_numbers[-1] if inline_numbers else None
                        # A trailing integer after "Minimum Payable Amount" is often a footnote marker.
                        if attr == "minimum_payable_amount" and inline_value and "." not in inline_value and "," not in inline_value:
                            inline_value = None
                        amount = clean_num(inline_value) if inline_value else (clean_num(next_value) if re.fullmatch(r"\s*[:?$]?\s*[\d,]+(?:\.\d+)?\s*", next_value) else None)
                        if amount is not None:
                            setattr(semantic.money, attr, amount)
                            if attr == "previous_dues": semantic.money.arrears = amount
                            add_evidence(evidence_name, amount, table_name=table.table_id, page=table.page, source_text=f"{label_text}: {amount}", confidence=table.confidence, bbox=table.bbox)
                        break

            # A. Table 1: Bill Details / Charges Table
            if "Bill Details" in tbl_title or "à¤¬à¤¿à¤² à¤µà¤¿à¤µà¤°à¤£" in tbl_title or "Table 1" in tbl_title:
                for r in table.rows:
                    if len(r) >= 2:
                        label_1, val_1 = str(r[0]), str(r[1])
                        num_1 = clean_num(val_1)
                        if label_1 and num_1 is not None:
                            chg = ChargeItem(
                                charge_id=f"chg_{len(semantic.charges)+1}",
                                label=label_1,
                                amount=num_1,
                                category=self._categorize_charge(label_1),
                                source_table=table.table_id
                            )
                            semantic.charges.append(chg)
                            self._map_money_field(label_1, num_1, semantic.money)

                    if len(r) >= 4:
                        label_2, val_2 = str(r[2]), str(r[3])
                        num_2 = clean_num(val_2)
                        if label_2 and num_2 is not None:
                            chg = ChargeItem(
                                charge_id=f"chg_{len(semantic.charges)+1}",
                                label=label_2,
                                amount=num_2,
                                category=self._categorize_charge(label_2),
                                source_table=table.table_id
                            )
                            semantic.charges.append(chg)
                            self._map_money_field(label_2, num_2, semantic.money)

            # B. Table 2: Calculation Details (Tariff Slabs)
            elif "Calculation Details" in tbl_title or "à¤—à¤£à¤¨à¤¾ à¤µà¤¿à¤µà¤°à¤£" in tbl_title or "Slab" in tbl_text or "Table 2" in tbl_title:
                for r in table.rows:
                    if len(r) >= 4 and any(s in str(r) for s in ["0-100", "101-150", "151-300", "Above"]):
                        slab_range = str(r[1]) if len(r) > 1 else None
                        units = clean_num(r[2]) if len(r) > 2 else None
                        net_payable = clean_num(r[-1]) if len(r) > 4 else None
                        gross_amt = clean_num(r[4]) if len(r) > 4 else None
                        
                        slab = TariffSlab(
                            slab_range=slab_range,
                            units=units,
                            gross_amount=gross_amt,
                            net_payable=net_payable
                        )
                        semantic.tariff_slabs.append(slab)

            # C. Table 3: Other Charges
            elif "Other Charges" in tbl_title or "à¤…à¤¨à¥à¤¯ à¤šà¤¾à¤°à¥à¤œà¥‡à¤œ" in tbl_title or "Table 3" in tbl_title:
                for r in table.rows:
                    if len(r) >= 2:
                        l1, v1 = str(r[0]), clean_num(r[1])
                        if l1 and v1 is not None:
                            semantic.charges.append(ChargeItem(
                                charge_id=f"chg_{len(semantic.charges)+1}",
                                label=l1, amount=v1, category="other", source_table=table.table_id
                            ))
                    if len(r) >= 4:
                        l2, v2 = str(r[2]), clean_num(r[3])
                        if l2 and v2 is not None:
                            semantic.charges.append(ChargeItem(
                                charge_id=f"chg_{len(semantic.charges)+1}",
                                label=l2, amount=v2, category="other", source_table=table.table_id
                            ))

            # D. Table 5: Last Payment Details
            elif "Last Payment" in tbl_title or "à¤…à¤‚à¤¤à¤¿à¤® à¤­à¥à¤—à¤¤à¤¾à¤¨" in tbl_title or "Table 5" in tbl_title:
                for r in table.rows:
                    if len(r) >= 4 and re.search(r"\d{1,2}\-[A-Za-z]{3}\-\d{4}", str(r[0])):
                        semantic.payment.last_payment_date = str(r[0])
                        semantic.payment.last_payment_amount = clean_num(r[1])
                        semantic.payment.last_payment_mode = str(r[2])
                        semantic.payment.last_receipt_number = str(r[3])

            # E. Table 6: Last Six Months Consumption
            elif "Last Six month" in tbl_title or "à¤µà¤¿à¤—à¤¤ à¤›" in tbl_title or "Table 6" in tbl_title:
                for r in table.rows:
                    if len(r) >= 4 and any(m in str(r[1]).upper() for m in ["AUG", "JUL", "JUN", "MAY", "APR", "MAR", "DEC", "NOV", "OCT", "SEP", "JAN", "FEB"]):
                        semantic.consumption_history.append(ConsumptionHistoryItem(
                            period=str(r[1]),
                            demand_kw=clean_num(r[2]),
                            units=clean_num(r[3])
                        ))

            # F. Table 7: Meter Reading Details
            elif "Meter Reading Details" in tbl_title or "à¤®à¥€à¤Ÿà¤° à¤¸à¤‚à¤–à¥à¤¯à¤¾" in tbl_text or "Table 7" in tbl_title:
                for r in table.rows:
                    if len(r) >= 5 and any(unit in str(r).upper() for unit in ["KWH", "UNITS", "KVAH"]):
                        dates = [cell for cell in r if re.search(r"\d{1,2}\-[A-Za-z]{3}\-\d{4}", str(cell))]
                        readings = [clean_num(cell) for cell in r[1:] if clean_num(cell) is not None and not re.search(r"\d{1,2}\-[A-Za-z]{3}\-\d{4}", str(cell)) and len(str(int(clean_num(cell)))) < 7]
                        
                        if len(dates) >= 2:
                            semantic.meter.previous_reading_date = str(dates[0])
                            semantic.meter.current_reading_date = str(dates[1])
                        if len(readings) >= 3:
                            semantic.meter.previous_reading = readings[0]
                            semantic.meter.current_reading = readings[1]
                            semantic.meter.reading_difference = readings[2]
                            semantic.meter.units_consumed = readings[2]
                            semantic.meter.meter_multiplier = 1.0

        # Preserve multiple competing generic field candidates for conflict checks.
        candidate_labels = {
            "account.account_number": ("account no", "consumer no", "consumer number", "\u0905\u0915\u093e\u0909\u0902\u091f \u0938\u0902", "\u0917\u094d\u0930\u093e\u0939\u0915 \u0915\u094d\u0930\u092e\u093e\u0902\u0915", "\u0916\u093e\u0924\u093e \u0915\u094d\u0930\u092e\u093e\u0902\u0915"),
            "account.bill_number": ("bill no", "bill number", "\u092c\u093f\u0932 \u0938\u0902\u0916\u094d\u092f\u093e"),
            "money.previous_dues": ("previous dues", "arrear amount", "\u092a\u0942\u0930\u094d\u0935 \u092c\u0915\u093e\u092f\u093e"),
            "money.current_bill_amount": ("current bill amount",),
            "money.payable_amount": ("payable amount", "total payable"),
            "meter.units_consumed": ("consumption", "units consumed"),
        }
        for target, labels in candidate_labels.items():
            candidates = []
            for source_field in doc.fields:
                source_label = source_field.label.casefold()
                if any(label in source_label for label in labels):
                    candidates.append(EvidenceItem(field=target, value=source_field.normalized_value if source_field.normalized_value is not None else source_field.value, page=source_field.page, source_text=source_field.source.text, confidence=source_field.confidence, bbox=source_field.source.bbox))
            if candidates:
                semantic.candidates[target] = candidates

        # Attach source evidence to every populated semantic leaf when a matching
        # generic field, OCR block, or table row can be identified. Never fabricate a bbox.
        existing = {item.field for item in evidence_list}
        payload = semantic.model_dump(exclude={"evidence", "candidates"})
        def visit(value, prefix=""):
            if isinstance(value, dict):
                for key, child in value.items():
                    visit(child, f"{prefix}.{key}" if prefix else key)
            elif isinstance(value, list):
                for index, child in enumerate(value): visit(child, f"{prefix}.{index}")
            elif value is not None and value != "" and prefix not in existing:
                needle = str(value).casefold()
                field_match = next((f for f in doc.fields if needle in str(f.value).casefold() or needle in str(f.normalized_value).casefold()), None)
                if field_match:
                    evidence_list.append(EvidenceItem(field=prefix, value=value, page=field_match.page, source_text=field_match.source.text, confidence=field_match.confidence, bbox=field_match.source.bbox))
                    existing.add(prefix); return
                for table in doc.tables:
                    for row in table.rows:
                        row_text = " | ".join(str(cell) for cell in row)
                        if needle and needle in row_text.casefold():
                            evidence_list.append(EvidenceItem(field=prefix, value=value, page=table.page, source_table=table.title or table.table_id, source_text=row_text, confidence=table.confidence, bbox=table.bbox))
                            existing.add(prefix); return
        visit(payload)
        semantic.evidence = evidence_list
        return semantic

    def _categorize_charge(self, label: str) -> str:
        lbl_lower = label.lower()
        if "energy" in lbl_lower or "à¤Šà¤°à¥à¤œà¤¾" in lbl_lower:
            return "energy"
        elif "demand" in lbl_lower or "fixed" in lbl_lower or "à¤®à¤¾à¤‚à¤—" in lbl_lower:
            return "demand"
        elif "duty" in lbl_lower or "à¤•à¤°" in lbl_lower:
            return "duty"
        elif "fppa" in lbl_lower or "fuel" in lbl_lower or "à¤ˆà¤‚à¤§à¤¨" in lbl_lower:
            return "fppa"
        elif "lpsc" in lbl_lower or "late" in lbl_lower or "à¤…à¤§à¤¿à¤­à¤¾à¤°" in lbl_lower:
            return "lpsc"
        elif "arrear" in lbl_lower or "à¤¬à¤•à¤¾à¤¯à¤¾" in lbl_lower:
            return "arrears"
        elif "rebate" in lbl_lower or "subsidy" in lbl_lower or "à¤›à¥‚à¤Ÿ" in lbl_lower:
            return "subsidy"
        return "other"

    def _map_money_field(self, label: str, val: float, money: BillMoney):
        lbl_lower = label.lower()
        if "arrear amount" in lbl_lower or "previous dues" in lbl_lower or "à¤¬à¤•à¤¾à¤¯à¤¾ à¤§à¤¨à¤°à¤¾à¤¶à¤¿" in lbl_lower:
            # Previous dues and arrears are sourced only from their labeled row.
            money.arrears = val
            money.previous_dues = val
        elif "current bill amount" in lbl_lower or "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤¬à¤¿à¤² à¤°à¤¾à¤¶à¤¿" in lbl_lower or "à¤šà¤¾à¤²à¥‚ à¤¦à¥‡à¤¯à¤•" in lbl_lower:
            money.current_bill_amount = val
        elif "payable amount" in lbl_lower or "total payable" in lbl_lower or "à¤•à¥à¤² à¤¦à¥‡à¤¯ à¤°à¤¾à¤¶à¤¿" in lbl_lower:
            money.payable_amount = val
        elif "current lpsc" in lbl_lower:
            money.late_payment_surcharge = val



