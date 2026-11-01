#!/usr/bin/env python3
"""
Pre-download and cache bodhan-ai/indic-ocr weights for instant offline execution.
"""
import sys
import logging
from huggingface_hub import snapshot_download

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("model_downloader")

MODEL_REPO = "bodhan-ai/indic-ocr"

def main():
    logger.info(f"Checking / downloading model weights for {MODEL_REPO}...")
    try:
        path = snapshot_download(MODEL_REPO, local_files_only=True)
        logger.info(f"[OK] Model already cached locally at: {path}")
        return 0
    except Exception:
        logger.info(f"Model not found in local cache. Downloading snapshot from Hugging Face...")
        try:
            path = snapshot_download(MODEL_REPO)
            logger.info(f"[SUCCESS] Model snapshot successfully downloaded to: {path}")
            return 0
        except Exception as ex:
            logger.error(f"[ERROR] Failed to download model: {ex}")
            return 1

if __name__ == "__main__":
    sys.exit(main())
