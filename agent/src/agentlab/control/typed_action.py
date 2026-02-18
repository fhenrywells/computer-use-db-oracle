from typing import Any

from agentlab.control.planner import pick_best_action
from agentlab.control.priors import score_action


def _view_priors(catalog: dict[str, Any], view_id: str) -> dict[str, float]:
    for view in catalog.get("views", []):
        if view.get("view_id") == view_id:
            return view.get("priors", {}).get("action_weights", {})
    return {}


def _desired_sort_for_task(task: dict[str, Any]) -> str:
    spec = task.get("spec", {})
    sort = spec.get("sort")
    if isinstance(sort, str):
        return sort
    otype = task.get("oracle", {}).get("type")
    if otype == "min_price_match":
        return "price_asc"
    if otype == "max_rating_match":
        return "rating_desc"
    return "relevance"


def next_action(
    task: dict[str, Any],
    observation: dict[str, Any],
    catalog: dict[str, Any],
    oracle_target_asin: str | None = None,
) -> dict[str, Any]:
    view_id = observation.get("view_id", "UNKNOWN")
    priors = _view_priors(catalog, view_id)
    candidates: list[dict[str, Any]] = []
    constraints = task.get("spec", {}).get("constraints", {})
    workload = task.get("workload_type")

    def add(action_type: str, args: dict[str, Any], bonus: float = 0.0) -> None:
        candidates.append({"type": action_type, "args": args, "score": score_action(action_type, priors) + bonus})

    if view_id == "HOME":
        query = task.get("spec", {}).get("query")
        if isinstance(query, str) and query.strip():
            add("Search", {"query": query}, bonus=1.0)
    elif view_id in {"SEARCH_RESULTS", "EMPTY_RESULTS"}:
        desired_sort = _desired_sort_for_task(task)
        if observation.get("sort_key") != desired_sort:
            add("SortBy", {"key": desired_sort}, bonus=0.8)

        applied = observation.get("applied_constraints", {})
        if isinstance(constraints, dict):
            for key in ["brand", "category_leaf", "price_bucket"]:
                if key in constraints and key not in applied:
                    facet = "category" if key == "category_leaf" else key
                    add("ApplyFacet", {"facet": facet, "value": constraints[key]}, bonus=0.9)
            if "rating_gte" in constraints and "rating_bucket" not in applied:
                add("ApplyFacet", {"facet": "rating_bucket", "value": str(constraints["rating_gte"])}, bonus=0.7)

        asins = observation.get("result_asins", [])
        if isinstance(asins, list) and asins:
            if oracle_target_asin and oracle_target_asin in asins:
                rank = asins.index(oracle_target_asin) + 1
                add("OpenResult", {"rank": rank}, bonus=1.5)
            else:
                add("OpenResult", {"rank": 1}, bonus=0.5)
    elif view_id == "PRODUCT_DETAIL":
        selected = observation.get("selected_asin")
        if workload == "graph_browse_related":
            related_asins = observation.get("related_asins", [])
            if oracle_target_asin and selected == oracle_target_asin:
                add("AddToCart", {"qty": 1}, bonus=1.8)
            elif oracle_target_asin and isinstance(related_asins, list) and oracle_target_asin in related_asins:
                rank = related_asins.index(oracle_target_asin) + 1
                add("OpenRelated", {"rank": rank}, bonus=1.3)
            elif isinstance(related_asins, list) and related_asins:
                add("OpenRelated", {"rank": 1}, bonus=0.8)
            else:
                add("BackToResults", {}, bonus=0.1)
        else:
            if oracle_target_asin and selected == oracle_target_asin:
                add("AddToCart", {"qty": 1}, bonus=1.5)
            else:
                add("AddToCart", {"qty": 1}, bonus=0.8)
            add("BackToResults", {}, bonus=0.2)
    elif view_id == "CART":
        add("NoOp", {"reason": "cart_reached"}, bonus=0.1)
    else:
        add("NoOp", {"reason": "unknown_view"}, bonus=0.0)

    return pick_best_action(candidates)
