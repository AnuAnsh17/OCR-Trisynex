import pymupdf
from pathlib import Path

pdf_path = Path(r"C:\Users\anura\Desktop\urja-ocr\data\uploads\test_bill.pdf")
output_dir = Path(r"C:\Users\anura\Desktop\urja-ocr\data\uploads\bill_pages")

output_dir.mkdir(parents=True, exist_ok=True)

doc = pymupdf.open(pdf_path)

print(f"PDF has {len(doc)} pages.")

for i, page in enumerate(doc):
    pix = page.get_pixmap(
        matrix=pymupdf.Matrix(2, 2),
        alpha=False
    )

    output_path = output_dir / f"page_{i + 1}.png"
    pix.save(str(output_path))

    print(f"Saved: {output_path}")

doc.close()

print("\nPDF → images complete.")