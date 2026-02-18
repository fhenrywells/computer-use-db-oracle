from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any


def _mistral_ocr(image_path: str | Path) -> str:
    api_key = os.getenv("MISTRAL_API_KEY", "").strip()
    if not api_key:
        return ""
    try:
        import requests
    except ModuleNotFoundError:
        return ""

    p = Path(image_path)
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    payload = {
        "model": "mistral-ocr-latest",
        "document": {"type": "image_url", "image_url": f"data:image/png;base64,{b64}"},
    }
    try:
        resp = requests.post(
            "https://api.mistral.ai/v1/ocr",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=30,
        )
        if resp.status_code >= 300:
            return ""
        data = resp.json()
        pages = data.get("pages", [])
        texts = [str(p.get("markdown", "")) for p in pages if isinstance(p, dict)]
        return "\n".join(texts).strip()
    except Exception:
        return ""


def _tesseract_ocr(image_path: str | Path) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ModuleNotFoundError:
        return ""

    try:
        with Image.open(image_path) as img:
            return pytesseract.image_to_string(img).strip()
    except Exception:
        return ""


def extract_ocr_text(image_path: str | Path) -> dict[str, Any]:
    # Try Mistral OCR first if configured, then local tesseract.
    txt = _mistral_ocr(image_path)
    provider = "mistral_ocr"
    if not txt:
        txt = _tesseract_ocr(image_path)
        provider = "tesseract"
    return {"provider": provider if txt else "none", "text": txt or ""}
