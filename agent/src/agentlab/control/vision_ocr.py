from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from agentlab.perception.ocr import extract_ocr_text


def _infer_view(text: str) -> str:
    t = text.lower()
    if "add to cart" in t and "related" in t:
        return "PRODUCT_DETAIL"
    if "add to cart" in t and "back to results" in t:
        return "PRODUCT_DETAIL"
    if "search products" in t and "go to cart" in t:
        return "HOME"
    if "empty cart" in t or "cart_count" in t and "search products" not in t:
        return "CART"
    if "no results" in t:
        return "EMPTY_RESULTS"
    if "result" in t or "brand" in t or "category" in t or "open" in t:
        return "SEARCH_RESULTS"
    return "UNKNOWN"


def _has_keyword(text: str, keyword: str) -> bool:
    return re.search(rf"\b{re.escape(keyword.lower())}\b", text.lower()) is not None


def next_action(task: dict[str, Any], visual_obs: dict[str, Any]) -> dict[str, Any]:
    shot = visual_obs.get("screenshot_path", "")
    text = ""
    ocr_provider = "none"
    if shot and Path(shot).exists():
        ocr = extract_ocr_text(shot)
        text = str(ocr.get("text", ""))
        ocr_provider = str(ocr.get("provider", "none"))

    inferred_view = _infer_view(text) if text else str(visual_obs.get("view_id", "UNKNOWN"))
    workload = task.get("workload_type")
    add_to_cart_count = int(visual_obs.get("add_to_cart_count", 0))
    opened_related_count = int(visual_obs.get("opened_related_count", 0))

    debug = {"ocr_provider": ocr_provider, "inferred_view": inferred_view}

    if inferred_view == "HOME":
        query = str(task.get("spec", {}).get("query", "")).strip()
        if query:
            return {"type": "Search", "args": {"query": query}, "_debug": debug}
        return {"type": "NoOp", "args": {"reason": "no_query"}, "_debug": debug}

    if inferred_view in {"SEARCH_RESULTS", "EMPTY_RESULTS"}:
        if _has_keyword(text, "no") and _has_keyword(text, "results"):
            return {"type": "NoOp", "args": {"reason": "ocr_no_results"}, "_debug": debug}
        return {"type": "OpenResult", "args": {"rank": 1}, "_debug": debug}

    if inferred_view == "PRODUCT_DETAIL":
        if workload == "graph_browse_related" and opened_related_count < 1 and _has_keyword(text, "related"):
            return {"type": "OpenRelated", "args": {"rank": 1}, "_debug": debug}
        if add_to_cart_count < 1 and _has_keyword(text, "add"):
            return {"type": "AddToCart", "args": {"qty": 1}, "_debug": debug}
        return {"type": "NoOp", "args": {"reason": "ocr_product_done"}, "_debug": debug}

    return {"type": "NoOp", "args": {"reason": "ocr_unknown"}, "_debug": debug}
