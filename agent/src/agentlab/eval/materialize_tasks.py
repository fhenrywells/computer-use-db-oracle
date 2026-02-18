from __future__ import annotations

from copy import deepcopy
from random import Random
from typing import Any


def _sample_product(products: list[dict[str, Any]], where: dict[str, Any] | None, rng: Random) -> dict[str, Any]:
    def matches(prod: dict[str, Any]) -> bool:
        if not where:
            return True
        for k, v in where.items():
            if isinstance(v, dict) and "$exists" in v:
                exists = k in prod and prod.get(k) is not None
                if exists != bool(v["$exists"]):
                    return False
            elif isinstance(v, dict) and "$gt" in v:
                if prod.get(k) is None or prod.get(k) <= v["$gt"]:
                    return False
            elif prod.get(k) != v:
                return False
        return True

    candidates = [p for p in products if matches(p)]
    if not candidates:
        raise ValueError("No products match sampling directive")
    return candidates[rng.randrange(len(candidates))]


def _derive_query_from(record: dict[str, Any], fields: list[str], max_tokens: int) -> str:
    tokens: list[str] = []
    for field in fields:
        value = str(record.get(field, "")).strip()
        if value:
            tokens.extend(value.split())
    return " ".join(tokens[:max_tokens]).strip()


def _resolve(node: Any, bindings: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        if "$derive_from" in node:
            ref = node["$derive_from"]
            return bindings[ref["var"]][ref["field"]]
        if "$derive_query_from" in node:
            ref = node["$derive_query_from"]
            source = bindings[ref["var"]]
            fields = ref.get("fields", [])
            max_tokens = int(ref.get("max_tokens", 6))
            return _derive_query_from(source, fields, max_tokens)
        if "$derive_range" in node:
            ref = node["$derive_range"]
            source = bindings[ref["var"]]
            value = float(source[ref["field"]])
            return round(value * float(ref.get("mult", 1.0)), 2)
        if "$derive_threshold" in node:
            ref = node["$derive_threshold"]
            source = bindings[ref["var"]]
            floor = float(ref.get("floor", 0.0))
            return max(float(source[ref["field"]]), floor)
        return {k: _resolve(v, bindings) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve(v, bindings) for v in node]
    return node


def materialize_task(template: dict[str, Any], products: list[dict[str, Any]], seed: int = 0) -> dict[str, Any]:
    rng = Random(seed)
    out = deepcopy(template)
    bindings: dict[str, Any] = {}

    spec = out.get("spec", {})
    seed_directive = spec.get("seed", {}).get("$sample_product")
    if seed_directive:
        bindings["P"] = _sample_product(products, seed_directive.get("where"), rng)

    out["spec"] = _resolve(spec, bindings)
    out["oracle"] = _resolve(out.get("oracle", {}), bindings)
    out["task_materialized"] = True
    return out
