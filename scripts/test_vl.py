from paddleocr import PaddleOCRVL

print("Loading PaddleOCR-VL...")

pipeline = PaddleOCRVL(
    device="gpu:0"
)

print("Processing document...")

output = pipeline.predict(
    "data/uploads/test_bill.pdf"
)

for res in output:
    res.print()
    res.save_to_json("data/outputs")
    res.save_to_markdown("data/outputs")

print("Done.")