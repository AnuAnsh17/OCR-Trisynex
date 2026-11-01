import httpx
import json
from pathlib import Path

def main():
    pdf_file = Path("data/uploads/test_bill.pdf")
    if not pdf_file.exists():
        print("Test PDF file not found!")
        return

    url = "http://127.0.0.1:8000/api/ingest"
    print(f"Uploading {pdf_file.name} to {url}...")
    
    with open(pdf_file, "rb") as f:
        files = {"file": (pdf_file.name, f, "application/pdf")}
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, files=files)

    print("Status Code:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        print("Document ID:", data.get("document_id"))
        print("JSON Path:", data.get("json_path"))
        print("Payable Amount:", data.get("result", {}).get("billing", {}).get("payable_amount"))
        print("Units Consumed:", data.get("result", {}).get("meter", {}).get("units_consumed"))
        print("Validation Checks:")
        for check in data.get("result", {}).get("validation", {}).get("checks", []):
            print(f"  - [{check['status']}] {check['name']}: {check['message']}")
    else:
        print("Error Response:", resp.text)

if __name__ == "__main__":
    main()
