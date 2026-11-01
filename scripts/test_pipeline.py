import json
from pathlib import Path
from backend.services.generic_builder import GenericDocumentBuilder
from backend.services.semantic.electricity_adapter import ElectricityBillAdapter
from backend.services.validator import UrjaValidator

def main():
    raw_file = Path("data/indicocr_results/all_pages.json")
    if not raw_file.exists():
        print("Raw results file not found!")
        return

    with open(raw_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    builder = GenericDocumentBuilder()
    adapter = ElectricityBillAdapter()
    validator = UrjaValidator()

    # 1. Lossless Generic Document Representation
    generic_doc = builder.build("test_doc_refactored", "test_bill.pdf", raw_data)

    # 2. Domain Semantic Extraction (Electricity Adapter)
    semantic_doc = adapter.adapt(generic_doc)

    # 3. Deterministic Validation
    val_res = validator.validate(semantic_doc)

    print("=" * 70)
    print("GENERIC DOCUMENT SUMMARY")
    print("=" * 70)
    print(f"Document ID     : {generic_doc.document.id}")
    print(f"Document Type   : {generic_doc.document.document_type} (conf: {generic_doc.document.document_type_confidence})")
    print(f"Page Count      : {generic_doc.document.page_count}")
    print(f"Detected Tables : {len(generic_doc.tables)}")
    print(f"Detected Fields : {len(generic_doc.fields)}")
    print(f"Detected Sections: {len(generic_doc.sections)}")

    print("\n" + "=" * 70)
    print("ALL DETECTED GENERIC TABLES")
    print("=" * 70)
    for idx, tbl in enumerate(generic_doc.tables, start=1):
        print(f"\n[{idx}] {tbl.title} (Page {tbl.page}, Rows: {len(tbl.rows)}, Cols: {len(tbl.columns)})")
        if tbl.rows:
            print("    First Row:", tbl.rows[0])

    print("\n" + "=" * 70)
    print("ELECTRICITY SEMANTIC DATA")
    print("=" * 70)
    print(f"Provider           : {semantic_doc.provider.name}")
    print(f"Account / Consumer : {semantic_doc.account.account_number}")
    print(f"Customer Name      : {semantic_doc.customer.name}")
    print(f"Sanctioned Load    : {semantic_doc.connection.sanctioned_load_kw} kW")
    print(f"Billed Demand      : {semantic_doc.connection.billed_demand_kw} kW")
    print(f"Current Bill Amount: ₹{semantic_doc.money.current_bill_amount}")
    print(f"Arrears            : ₹{semantic_doc.money.arrears}")
    print(f"Payable Amount     : ₹{semantic_doc.money.payable_amount}")
    print(f"Meter Number       : {semantic_doc.meter.meter_number}")
    print(f"Units Consumed     : {semantic_doc.meter.units_consumed} kWh")
    print(f"Tariff Slabs       : {len(semantic_doc.tariff_slabs)} slabs")
    print(f"Charges Captured   : {len(semantic_doc.charges)} individual charges")
    print(f"Consumption History: {len(semantic_doc.consumption_history)} months")

    print("\n" + "=" * 70)
    print("VALIDATION CHECKS")
    print("=" * 70)
    for check in val_res.checks:
        print(f"  [{check.status.upper()}] {check.name}: {check.message}")

if __name__ == "__main__":
    main()
