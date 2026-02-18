from __future__ import annotations

from copy import deepcopy
from random import Random
from typing import Any


def _derive_query_from(record: dict[str, Any], fields: list[str], max_tokens: int) -> str:
    tokens: list[str] = []
    for field in fields:
        value = str(record.get(field, "")).strip()
        if value:
            tokens.extend(value.split())
    return " ".join(tokens[:max_tokens]).strip()


def _resolve_node(node: Any, bindings: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        if "$derive_from" in node:
            ref = node["$derive_from"]
            return bindings[ref["var"]].get(ref["field"])
        if "$derive_query_from" in node:
            ref = node["$derive_query_from"]
            return _derive_query_from(bindings[ref["var"]], ref.get("fields", []), int(ref.get("max_tokens", 6)))
        if "$derive_range" in node:
            ref = node["$derive_range"]
            raw = bindings[ref["var"]].get(ref["field"])
            if raw is None:
                return None
            base = float(raw)
            return round(base * float(ref.get("mult", 1.0)), 2)
        if "$derive_threshold" in node:
            ref = node["$derive_threshold"]
            raw = bindings[ref["var"]].get(ref["field"])
            if raw is None:
                return float(ref.get("floor", 0.0))
            val = float(raw)
            return max(val, float(ref.get("floor", 0.0)))
        return {k: _resolve_node(v, bindings) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_node(v, bindings) for v in node]
    return node


def _pick_graph_target(products_col, seed_product: dict[str, Any], edge: str) -> tuple[str | None, str]:
    related = seed_product.get("related") if isinstance(seed_product.get("related"), dict) else {}
    preferred_edges = [edge, "bought_together", "also_viewed", "also_bought"]
    seen: set[str] = set()
    for e in preferred_edges:
        if e in seen:
            continue
        seen.add(e)
        raw = related.get(e)
        if isinstance(raw, str):
            candidates = [raw]
        elif isinstance(raw, list):
            candidates = [str(x) for x in raw if str(x).strip()]
        else:
            candidates = []
        if not candidates:
            continue
        hit = products_col.find_one({"asin": {"$in": candidates}}, {"asin": 1})
        if hit:
            return hit["asin"], e

    seed_asin = seed_product.get("asin")
    seed_brand = seed_product.get("brand")
    seed_category = seed_product.get("category_leaf")
    if seed_brand:
        hit = products_col.find_one({"asin": {"$ne": seed_asin}, "brand": seed_brand}, {"asin": 1})
        if hit:
            return hit["asin"], "brand_fallback"
    if seed_category:
        hit = products_col.find_one({"asin": {"$ne": seed_asin}, "category_leaf": seed_category}, {"asin": 1})
        if hit:
            return hit["asin"], "category_fallback"

    hit = products_col.find_one({"asin": {"$ne": seed_asin}}, {"asin": 1})
    return (hit["asin"], "random_fallback") if hit else (None, "none")


def resolve_task_template(task_template: dict[str, Any], products_col, seed: int = 0) -> dict[str, Any]:
    task = deepcopy(task_template)
    rng = Random(seed)
    bindings: dict[str, Any] = {}

    spec = task.get("spec", {})
    sample_directive = spec.get("seed", {}).get("$sample_product") if isinstance(spec.get("seed"), dict) else None
    if sample_directive:
        where = sample_directive.get("where", {})
        pipeline = [{"$match": where}, {"$sample": {"size": 1}}]
        picked = list(products_col.aggregate(pipeline))
        if not picked:
            fallback = list(products_col.aggregate([{"$sample": {"size": 1}}]))
            if not fallback:
                raise ValueError(f"No products available to sample for task {task.get('task_id')}")
            picked = fallback
            task["resolver_warning"] = f"seed sampling fallback used for task {task.get('task_id')}"
        bindings["P"] = picked[0]

    task["spec"] = _resolve_node(spec, bindings)
    task["oracle"] = _resolve_node(task.get("oracle", {}), bindings)
    task["task_materialized"] = True
    task["seed"] = seed
    if "P" in bindings:
        task["sampled_product"] = {"asin": bindings["P"].get("asin"), "title": bindings["P"].get("title")}

    if task.get("workload_type") == "graph_browse_related" and "P" in bindings:
        edge = str(task.get("spec", {}).get("edge", "also_bought"))
        start_asin = bindings["P"].get("asin")
        target_asin, edge_used = _pick_graph_target(products_col, bindings["P"], edge)
        task.setdefault("spec", {})
        task["spec"]["start_asin"] = start_asin
        task["spec"]["target_asin"] = target_asin
        task["spec"]["edge_used"] = edge_used
        task.setdefault("oracle", {})
        if task["oracle"].get("type") == "related_edge_match":
            task["oracle"]["expected_asin"] = target_asin

    # Add jitter so repeated runs vary sample choice when same base seed is used.
    rng.random()
    return task
