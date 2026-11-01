import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from PIL import Image

from backend.services.classifier import classify_document_type
from backend.services.generic_builder import GenericDocumentBuilder
from backend.services.ocr_service import prepare_sources, process_page_images
from backend.services.semantic.electricity_adapter import ElectricityBillAdapter

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "ocr_results" / "3f5ec0f9174d" / "indicocr_raw.json"


class PagePipelineTests(unittest.TestCase):
    def test_pdf_pages_are_ordered(self):
        from backend.services.ocr_service import rasterize_pdf
        pdf = ROOT / "data" / "uploads" / "test_bill.pdf"
        with tempfile.TemporaryDirectory() as tmp:
            pages = rasterize_pdf(pdf, Path(tmp))
        self.assertEqual([p.name for p in pages], [f"page_{n:03d}.png" for n in range(1, len(pages) + 1)])
        self.assertGreater(len(pages), 1)

    def test_single_image_is_prepared_as_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "camera.jpg"
            Image.new("RGB", (64, 96), "white").save(source)
            pages = prepare_sources([{"source_id":"source_001","source_filename":"camera.jpg","type":"image","path":str(source)}], Path(tmp) / "doc")
            self.assertEqual(len(pages), 1)
            self.assertEqual(pages[0]["source_page_number"], 1)
            self.assertTrue(Path(pages[0]["image_path"]).exists())

    def test_ocr_failure_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "page.png"
            Image.new("RGB", (16, 16), "white").save(image)
            source = {"source_id":"source_001","source_filename":"page.png","source_page_number":1,"image_path":str(image)}
            with patch("backend.services.ocr_service.get_indic_ocr_parser") as get_parser:
                get_parser.return_value.parse.side_effect = RuntimeError("mock OCR failure")
                raw, pages = process_page_images([source], "doc1", Path(tmp) / "doc1")
            self.assertEqual(pages[0]["status"], "failed")
            self.assertEqual(raw["status"], "completed_with_errors")
            self.assertIsNone(pages[0]["result"])


class GenericAndSemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.document = GenericDocumentBuilder().build("fixture", "test_bill.pdf", cls.raw)

    def test_raw_ocr_and_arbitrary_tables_survive(self):
        self.assertEqual(self.document.raw_ocr, self.raw)
        self.assertEqual(len(self.document.tables), 11)
        self.assertTrue(all(table.raw_html and table.raw_table == table.raw_html for table in self.document.tables))
        self.assertTrue(all(len({len(row) for row in table.rows}) <= 1 for table in self.document.tables))
        self.assertTrue(any(cell["rowspan"] > 1 or cell["colspan"] > 1 for table in self.document.tables for cell in table.cells))

    def test_unknown_document_keeps_generic_content(self):
        raw = {"pages":[{"page_number":1,"result":{"width":100,"height":100,"blocks":[{"order":0,"label":"Paragraph","type":"Text","bbox_xyxy":[1,2,3,4],"conf":0.8,"text":"An unfamiliar structured statement"}]}}]}
        doc = GenericDocumentBuilder().build("unknown", "unknown.png", raw)
        self.assertEqual(doc.document.document_type, "unknown")
        self.assertTrue(doc.pages[0].full_text)
        self.assertTrue(doc.additional_sections)

    def test_arrears_regression_uses_labeled_value(self):
        semantic = ElectricityBillAdapter().adapt(self.document)
        self.assertEqual(semantic.money.previous_dues, 0.49)
        self.assertEqual(semantic.money.current_bill_amount, 2414.98)
        self.assertEqual(semantic.money.payable_amount, 2415.0)

    def test_classifier_does_not_bias_zero_scores_to_electricity(self):
        self.assertEqual(classify_document_type("random multilingual content")[0], "unknown")
        self.assertEqual(classify_document_type("Gas bill piped gas SCM consumption")[0], "gas_bill")

    def test_conflicting_account_candidates_are_reported(self):
        from backend.services.validator import UrjaValidator
        raw = {"pages":[{"page_number":1,"result":{"blocks":[
            {"order":0,"label":"Text","type":"Text","conf":0.9,"bbox_xyxy":[0,0,10,10],"text":"Account No: 111"},
            {"order":1,"label":"Text","type":"Text","conf":0.8,"bbox_xyxy":[0,10,10,20],"text":"Account No: 222"}
        ]}}]}
        doc = GenericDocumentBuilder().build("conflict", "conflict.pdf", raw)
        semantic = ElectricityBillAdapter().adapt(doc)
        result = UrjaValidator().validate(semantic)
        self.assertEqual(result.status, "conflict")
        self.assertTrue(any(check.name == "evidence_conflict" for check in result.checks))
        self.assertEqual({str(x.value) for x in semantic.candidates["account.account_number"]}, {"111", "222"})

    def test_hindi_marathi_english_text_is_preserved(self):
        raw = {"pages":[{"page_number":1,"result":{"blocks":[{"order":0,"label":"Text","type":"Text","bbox_xyxy":[0,0,10,10],"conf":0.8,"text":"????? ??? / ??? ??? / Electricity Bill"}]}}]}
        doc = GenericDocumentBuilder().build("lang", "mixed.png", raw)
        self.assertIn("????? ???", doc.pages[0].full_text)
        self.assertIn("??? ???", doc.pages[0].full_text)
        self.assertEqual(doc.raw_ocr, raw)

    def test_conflicting_sources_remain_in_raw_document(self):
        raw = {"pages":[{"page_number":1,"result":{"blocks":[{"order":0,"label":"Text","type":"Text","conf":0.9,"bbox_xyxy":[0,0,1,1],"text":"Account No: 111"},{"order":1,"label":"Text","type":"Text","conf":0.8,"bbox_xyxy":[0,1,1,2],"text":"Account No: 222"}]}}]}
        doc = GenericDocumentBuilder().build("conflict", "conflict.png", raw)
        self.assertEqual(doc.raw_ocr, raw)
        self.assertEqual(len(doc.pages[0].blocks), 2)


class BatchApiTests(unittest.TestCase):
    def setUp(self):
        from backend import main
        self.main = main
        self.temp = tempfile.TemporaryDirectory()
        self.patch_dir = patch.object(main, "DOCUMENTS_DIR", Path(self.temp.name))
        self.patch_dir.start()
        self.client = TestClient(main.app)
        self.parser_patch = patch("backend.services.ocr_service.get_indic_ocr_parser")
        parser = self.parser_patch.start()
        parser.return_value.parse.return_value = {"width":100,"height":100,"blocks":[{"order":0,"label":"Text","type":"Text","bbox_xyxy":[0,0,10,10],"conf":0.9,"text":"Unknown note"}]}

    def tearDown(self):
        self.parser_patch.stop(); self.patch_dir.stop(); self.temp.cleanup()

    def test_single_pdf_is_one_document(self):
        pdf = (ROOT / "data" / "uploads" / "test_bill.pdf").read_bytes()
        response = self.client.post("/api/ingest", files=[("files", ("one.pdf", pdf, "application/pdf"))])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["documents"]), 1)
        self.assertEqual(response.json()["documents"][0]["document"]["document"]["page_count"], 4)

    def test_api_reports_failed_document_when_all_pages_fail(self):
        pdf = (ROOT / "data" / "uploads" / "test_bill.pdf").read_bytes()
        with patch("backend.services.ocr_service.get_indic_ocr_parser") as parser:
            parser.return_value.parse.side_effect = RuntimeError("mock failure")
            response = self.client.post("/api/ingest", files=[("files", ("failure.pdf", pdf, "application/pdf"))])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["documents"][0]["status"], "failed")

    def test_multiple_pdfs_are_separate_documents(self):
        pdf = (ROOT / "data" / "uploads" / "test_bill.pdf").read_bytes()
        response = self.client.post("/api/ingest", files=[("files",("a.pdf",pdf,"application/pdf")),("files",("b.pdf",pdf,"application/pdf"))])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["documents"]), 2)

    def test_multiple_images_group_as_one_document(self):
        from io import BytesIO
        def jpg():
            buf=BytesIO(); Image.new("RGB",(20,20),"white").save(buf,format="JPEG"); return buf.getvalue()
        response = self.client.post("/api/ingest", data={"group_images":"true"}, files=[("files",("page-a.jpg",jpg(),"image/jpeg")),("files",("page-b.jpg",jpg(),"image/jpeg"))])
        self.assertEqual(response.status_code, 200)
        body=response.json(); self.assertEqual(len(body["documents"]),1)
        self.assertEqual(body["documents"][0]["document"]["document"]["page_count"],2)
        self.assertEqual(len(body["documents"][0]["raw_ocr"]["sources"]),2)

    def test_mixed_pdf_and_image_keep_boundaries(self):
        from io import BytesIO
        buf=BytesIO(); Image.new("RGB",(20,20),"white").save(buf,format="PNG")
        pdf=(ROOT / "data" / "uploads" / "test_bill.pdf").read_bytes()
        response=self.client.post("/api/ingest",data={"group_images":"true"},files=[("files",("bill.pdf",pdf,"application/pdf")),("files",("photo.png",buf.getvalue(),"image/png"))])
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.json()["documents"]),2)


if __name__ == "__main__":
    unittest.main()
