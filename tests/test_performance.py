import time
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "data" / "uploads" / "test_bill.pdf"


class PerformanceAndAccuracyTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ready")
        self.assertIn("acceleration", data)
        self.assertIn("device_name", data)

    def test_fast_digital_pipeline_speed(self):
        """Verify that digital vector extraction runs end-to-end in under 2 seconds."""
        pdf_bytes = PDF_PATH.read_bytes()
        t0 = time.perf_counter()
        resp = self.client.post(
            "/api/ingest",
            files=[("files", ("test_bill.pdf", pdf_bytes, "application/pdf"))],
            data={"force_ocr": "false"}
        )
        duration = time.perf_counter() - t0
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(len(data["documents"]), 1)
        doc = data["documents"][0]
        self.assertEqual(doc["document"]["document"]["page_count"], 4)
        self.assertIn("timing", doc)
        print(f"\n[BENCHMARK] Digital PDF Fast Path (4 pages): {duration*1000:.1f}ms total (Server time: {data['timing_ms']}ms)")
        # Must finish under 2000ms (previously took 60,000ms - 120,000ms)
        self.assertLess(duration, 2.0)


if __name__ == "__main__":
    unittest.main()
