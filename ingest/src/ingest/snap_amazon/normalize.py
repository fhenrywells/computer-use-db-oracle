from __future__ import annotations

import re
from typing import Any


def _clean_price(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if match:
            return float(match.group(0))
    return None


def _normalize_categories(raw_categories: Any, fallback: str | None) -> tuple[list[str], str | None]:
    if isinstance(raw_categories, list):
        cats = [str(c).strip() for c in raw_categories if str(c).strip()]
    else:
        cats = []
    if not cats and fallback:
        cats = [fallback]
    category_leaf = cats[-1] if cats else None
    return cats, category_leaf


def _normalize_related(record: dict[str, Any]) -> dict[str, list[str]] | None:
    raw = record.get("bought_together")
    if isinstance(raw, list):
        vals = [str(v).strip() for v in raw if str(v).strip()]
        return {"bought_together": vals} if vals else None
    if isinstance(raw, str) and raw.strip():
        return {"bought_together": [raw.strip()]}
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        value = value.strip().replace(",", "")
        if value.isdigit():
            return int(value)
    return None


def normalize_record(record: dict[str, Any], source_file: str) -> dict[str, Any] | None:
    asin = record.get("parent_asin") or record.get("asin")
    title = record.get("title")
    if not asin or not title:
        return None

    categories, category_leaf = _normalize_categories(record.get("categories"), record.get("main_category"))

    doc: dict[str, Any] = {
        "asin": str(asin),
        "title": str(title).strip(),
        "price": _clean_price(record.get("price")),
        "brand": (record.get("store") or None),
        "category_leaf": category_leaf,
        "categories": categories,
        "main_category": record.get("main_category"),
        "rating_avg": _to_float(record.get("average_rating")),
        "rating_count": _to_int(record.get("rating_number")),
        "description": record.get("description"),
        "features": record.get("features"),
        "images": record.get("images"),
        "details": record.get("details"),
        "source": {
            "dataset": "McAuley-Lab/Amazon-Reviews-2023",
            "file": source_file,
        },
    }

    related = _normalize_related(record)
    if related:
        doc["related"] = related

    return doc
