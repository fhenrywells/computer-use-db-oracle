from __future__ import annotations

from typing import Any


def next_action(task: dict[str, Any], visual_obs: dict[str, Any]) -> dict[str, Any]:
    view_id = visual_obs.get("view_id")
    if view_id == "HOME":
        query = str(task.get("spec", {}).get("query", "")).strip()
        if query:
            return {"type": "Search", "args": {"query": query}}
        return {"type": "NoOp", "args": {"reason": "no_query"}}

    if view_id in {"SEARCH_RESULTS", "EMPTY_RESULTS"}:
        if int(visual_obs.get("result_count", 0)) > 0:
            return {"type": "OpenResult", "args": {"rank": 1}}
        return {"type": "NoOp", "args": {"reason": "no_results"}}

    if view_id == "PRODUCT_DETAIL":
        # Visual-only baseline: cannot reason over exact target paths.
        if task.get("workload_type") == "graph_browse_related" and visual_obs.get("has_related"):
            return {"type": "OpenRelated", "args": {"rank": 1}}
        return {"type": "AddToCart", "args": {"qty": 1}}

    return {"type": "NoOp", "args": {"reason": "fallback"}}
