from __future__ import annotations

from typing import Any


def next_action(task: dict[str, Any], visual_obs: dict[str, Any]) -> dict[str, Any]:
    view_id = visual_obs.get("view_id")
    add_to_cart_count = int(visual_obs.get("add_to_cart_count", 0))
    opened_related_count = int(visual_obs.get("opened_related_count", 0))
    workload = task.get("workload_type")
    if view_id == "HOME":
        query = str(task.get("spec", {}).get("query", "")).strip()
        if query:
            return {"type": "Search", "args": {"query": query}}
        return {"type": "NoOp", "args": {"reason": "no_query"}}

    if view_id in {"SEARCH_RESULTS", "EMPTY_RESULTS"}:
        # Screenshot-only baseline: no direct result_count/asin signals.
        return {"type": "OpenResult", "args": {"rank": 1}}

    if view_id == "PRODUCT_DETAIL":
        if workload == "graph_browse_related" and opened_related_count < 1:
            return {"type": "OpenRelated", "args": {"rank": 1}}
        # Prevent repetitive add loops: add once, then pause.
        if add_to_cart_count < 1:
            return {"type": "AddToCart", "args": {"qty": 1}}
        return {"type": "NoOp", "args": {"reason": "already_added_once"}}

    return {"type": "NoOp", "args": {"reason": "fallback"}}
