import os
import sys
import json
from pathlib import Path

from huggingface_hub import snapshot_download


# ============================================================
# CONFIG
# ============================================================

MODEL_REPO = "bodhan-ai/indic-ocr"

PAGES_DIR = Path(r"C:\Users\anura\Desktop\marathi bill")

OUTPUT_DIR = PAGES_DIR / "indicocr_results"

SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}


# ============================================================
# HELPERS
# ============================================================

def get_image_files(folder: Path):
    """Return all supported image files in alphabetical order."""
    if not folder.exists():
        raise FileNotFoundError(f"Input folder does not exist: {folder}")

    files = [
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    # WhatsApp filenames are not page_1/page_2 style,
    # so simple alphabetical sorting is safest.
    return sorted(files, key=lambda p: p.name.lower())


def save_json(path: Path, data):
    """Save JSON with UTF-8 encoding."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("INDICOCR MARATHI BILL TEST")
    print("=" * 70)

    print(f"\nInput folder:")
    print(PAGES_DIR)

    print(f"\nOutput folder:")
    print(OUTPUT_DIR)

    # --------------------------------------------------------
    # Check input folder
    # --------------------------------------------------------

    if not PAGES_DIR.exists():
        print("\nERROR: Input folder does not exist.")
        print(PAGES_DIR)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # Find images
    # --------------------------------------------------------

    pages = get_image_files(PAGES_DIR)

    if not pages:
        print("\nERROR: No supported images found.")
        print("Supported:", ", ".join(sorted(SUPPORTED_EXTENSIONS)))
        sys.exit(1)

    print(f"\nFound {len(pages)} image(s):\n")

    for i, page in enumerate(pages, start=1):
        print(f"  {i:02d}. {page.name}")

    # --------------------------------------------------------
    # Load IndicOCR
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("RESOLVING INDICOCR MODEL")
    print("=" * 70)

    repo_path = snapshot_download(MODEL_REPO)

    print(f"\nModel path:")
    print(repo_path)

    # Allow IndicOCR package to be imported from downloaded repo.
    sys.path.insert(0, repo_path)

    from indic_ocr import IndicOCR

    print("\nLoading IndicOCR...")

    parser = IndicOCR.from_pretrained(repo_path)

    print("Model loaded successfully.")

    # --------------------------------------------------------
    # Process pages
    # --------------------------------------------------------

    all_results = []

    print("\n" + "=" * 70)
    print("STARTING OCR")
    print("=" * 70)

    for index, image_path in enumerate(pages, start=1):

        print("\n" + "-" * 70)
        print(f"PAGE {index}/{len(pages)}")
        print("-" * 70)

        print(f"File: {image_path.name}")

        try:
            # ------------------------------------------------
            # Run IndicOCR
            # ------------------------------------------------

            result = parser.parse(str(image_path))

            # ------------------------------------------------
            # Add our own metadata
            # ------------------------------------------------

            page_result = {
                "page_number": index,
                "source_file": image_path.name,
                "source_path": str(image_path),
                "ocr_engine": "IndicOCR",
                "model": MODEL_REPO,
                "result": result,
            }

            # ------------------------------------------------
            # Save individual result
            # ------------------------------------------------

            output_file = OUTPUT_DIR / f"page_{index}.json"

            save_json(output_file, page_result)

            all_results.append(page_result)

            print(f"\nSUCCESS")
            print(f"Saved: {output_file}")

        except Exception as e:

            print("\nERROR processing this page:")
            print(str(e))

            error_result = {
                "page_number": index,
                "source_file": image_path.name,
                "source_path": str(image_path),
                "ocr_engine": "IndicOCR",
                "model": MODEL_REPO,
                "error": str(e),
            }

            all_results.append(error_result)

            output_file = OUTPUT_DIR / f"page_{index}_ERROR.json"

            save_json(output_file, error_result)

            print(f"Error saved: {output_file}")

    # --------------------------------------------------------
    # Save combined result
    # --------------------------------------------------------

    combined_result = {
        "project": "Urja",
        "ocr_engine": "IndicOCR",
        "model": MODEL_REPO,
        "input_folder": str(PAGES_DIR),
        "page_count": len(pages),
        "pages": all_results,
    }

    combined_file = OUTPUT_DIR / "all_pages.json"

    save_json(combined_file, combined_result)

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    successful = sum(
        1 for result in all_results
        if "error" not in result
    )

    failed = len(all_results) - successful

    print("\n")
    print("=" * 70)
    print("ALL PAGES COMPLETE")
    print("=" * 70)

    print(f"\nTotal images : {len(pages)}")
    print(f"Successful   : {successful}")
    print(f"Failed       : {failed}")

    print(f"\nIndividual results:")
    print(OUTPUT_DIR)

    print(f"\nCombined result:")
    print(combined_file)

    print("\n" + "=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()