from __future__ import annotations

from pathlib import Path
from typing import Any


_VIEW_RGB = {
    "HOME": (173, 40, 49),
    "SEARCH_RESULTS": (29, 78, 216),
    "EMPTY_RESULTS": (29, 78, 216),
    "PRODUCT_DETAIL": (15, 118, 110),
    "CART": (180, 83, 9),
}


def _distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def classify_view_from_screenshot(path: str | Path) -> tuple[str, float]:
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Pillow is required for screenshot classification. Install with `pip install pillow`."
        ) from exc

    p = Path(path)
    with Image.open(p) as img:
        rgb = img.convert("RGB")
        # UI banner is at top; sample center near top strip.
        w, h = rgb.size
        sample_y = max(1, min(h - 1, int(h * 0.03)))
        sample_x = max(1, min(w - 1, int(w * 0.5)))
        px = rgb.getpixel((sample_x, sample_y))
        if isinstance(px, int):
            color = (px, px, px)
        else:
            color = (int(px[0]), int(px[1]), int(px[2]))

    best_view = "UNKNOWN"
    best_dist = float("inf")
    for view, ref in _VIEW_RGB.items():
        d = _distance(color, ref)
        if d < best_dist:
            best_dist = d
            best_view = view

    confidence = max(0.0, min(1.0, 1.0 - best_dist / 255.0))
    return best_view, confidence


def screenshot_features(path: str | Path) -> dict[str, Any]:
    view_id, confidence = classify_view_from_screenshot(path)
    return {"view_id": view_id, "view_confidence": confidence, "screenshot_path": str(path)}
