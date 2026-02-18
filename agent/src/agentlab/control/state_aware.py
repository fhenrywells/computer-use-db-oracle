from typing import Any


def next_action(task: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    view_id = observation.get("view_id")
    if view_id == "HOME":
        query = str(task.get("spec", {}).get("query", "")).strip()
        if query:
            return {"type": "Search", "args": {"query": query}}
    if view_id in {"SEARCH_RESULTS", "EMPTY_RESULTS"}:
        return {"type": "OpenResult", "args": {"rank": 1}}
    if view_id == "PRODUCT_DETAIL":
        if task.get("workload_type") == "graph_browse_related":
            related_asins = observation.get("related_asins", [])
            target = task.get("spec", {}).get("target_asin")
            if target and observation.get("selected_asin") == target:
                return {"type": "AddToCart", "args": {"qty": 1}}
            if isinstance(related_asins, list) and related_asins:
                return {"type": "OpenRelated", "args": {"rank": 1}}
        return {"type": "AddToCart", "args": {"qty": 1}}
    return {"type": "NoOp", "args": {"reason": "state-aware fallback"}}
