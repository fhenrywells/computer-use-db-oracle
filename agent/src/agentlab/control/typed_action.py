from typing import Any

from agentlab.control.priors import (
    get_workload_view_priors,
    prune_candidates_by_prior,
    score_action,
)


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
    use_priors: bool = False,
    learned_priors_model: dict[str, Any] | None = None,
    prior_alpha: float = 1.2,
    repeat_beta: float = 0.35,
    prior_top_k: int = 3,
) -> dict[str, Any]:
    view_id = observation.get("view_id", "UNKNOWN")
    base_priors = _view_priors(catalog, view_id)
    candidates: list[dict[str, Any]] = []
    constraints = task.get("spec", {}).get("constraints", {})
    workload = task.get("workload_type")
    learned_priors = (
        get_workload_view_priors(learned_priors_model or {}, str(workload), str(view_id))
        if use_priors
        else {}
    )
    history = observation.get("_history", [])

    def add(action_type: str, args: dict[str, Any], task_score: float = 0.0) -> None:
        candidates.append({"type": action_type, "args": args, "task_score": task_score})

    if view_id == "HOME":
        query = task.get("spec", {}).get("query")
        if isinstance(query, str) and query.strip():
            add("Search", {"query": query}, task_score=1.0)
    elif view_id in {"SEARCH_RESULTS", "EMPTY_RESULTS"}:
        desired_sort = _desired_sort_for_task(task)
        if observation.get("sort_key") != desired_sort:
            add("SortBy", {"key": desired_sort}, task_score=0.8)

        applied = observation.get("applied_constraints", {})
        if isinstance(constraints, dict):
            for key in ["brand", "category_leaf", "price_bucket"]:
                if key in constraints and key not in applied:
                    facet = "category" if key == "category_leaf" else key
                    add("ApplyFacet", {"facet": facet, "value": constraints[key]}, task_score=0.9)
            if "rating_gte" in constraints and "rating_bucket" not in applied:
                add("ApplyFacet", {"facet": "rating_bucket", "value": str(constraints["rating_gte"])}, task_score=0.7)

        asins = observation.get("result_asins", [])
        if isinstance(asins, list) and asins:
            if oracle_target_asin and oracle_target_asin in asins:
                rank = asins.index(oracle_target_asin) + 1
                add("OpenResult", {"rank": rank}, task_score=1.5)
            else:
                add("OpenResult", {"rank": 1}, task_score=0.5)
    elif view_id == "PRODUCT_DETAIL":
        selected = observation.get("selected_asin")
        if workload == "graph_browse_related":
            related_asins = observation.get("related_asins", [])
            if oracle_target_asin and selected == oracle_target_asin:
                add("AddToCart", {"qty": 1}, task_score=1.8)
            elif oracle_target_asin and isinstance(related_asins, list) and oracle_target_asin in related_asins:
                rank = related_asins.index(oracle_target_asin) + 1
                add("OpenRelated", {"rank": rank}, task_score=1.3)
            elif isinstance(related_asins, list) and related_asins:
                add("OpenRelated", {"rank": 1}, task_score=0.8)
            else:
                add("BackToResults", {}, task_score=0.1)
        else:
            if oracle_target_asin and selected == oracle_target_asin:
                add("AddToCart", {"qty": 1}, task_score=1.5)
            else:
                add("AddToCart", {"qty": 1}, task_score=0.8)
            add("BackToResults", {}, task_score=0.2)
    elif view_id == "CART":
        add("NoOp", {"reason": "cart_reached"}, task_score=0.1)
    else:
        add("NoOp", {"reason": "unknown_view"}, task_score=0.0)

    if use_priors:
        candidates = prune_candidates_by_prior(candidates, base_priors, learned_priors, top_k=prior_top_k)

    for c in candidates:
        action_type = str(c["type"])
        repeat_count = sum(
            1
            for s in history
            if s.get("view_pred") == view_id and s.get("action", {}).get("type") == action_type
        )
        prior_term = score_action(
            action_type,
            base_priors=base_priors,
            learned_priors=learned_priors if use_priors else None,
            alpha=prior_alpha if use_priors else 0.0,
        )
        c["score"] = float(c.get("task_score", 0.0)) + prior_term - (repeat_beta * repeat_count)
        c["_debug"] = {
            "task_score": float(c.get("task_score", 0.0)),
            "prior_term": round(prior_term, 6),
            "repeat_count": repeat_count,
            "repeat_penalty": round(repeat_beta * repeat_count, 6),
            "score": round(c["score"], 6),
            "used_priors": use_priors,
        }

    if not candidates:
        return {"type": "NoOp", "args": {"reason": "no_candidates"}}
    best = sorted(candidates, key=lambda x: float(x.get("score", 0.0)), reverse=True)[0]
    return {"type": best["type"], "args": best["args"], "_debug": best.get("_debug", {})}
