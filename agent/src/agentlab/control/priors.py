from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def _normalize(weights: dict[str, float]) -> dict[str, float]:
    cleaned = {k: float(max(0.0, v)) for k, v in weights.items()}
    total = sum(cleaned.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in cleaned.items()}


def load_learned_priors(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"version": "1", "by_workload_view": {}}
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"version": "1", "by_workload_view": {}}
    data.setdefault("by_workload_view", {})
    return data


def save_learned_priors(path: str | Path, priors: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(priors, indent=2), encoding="utf-8")


def get_workload_view_priors(learned_priors: dict[str, Any], workload: str, view_id: str) -> dict[str, float]:
    by_wv = learned_priors.get("by_workload_view", {})
    raw = by_wv.get(workload, {}).get(view_id, {})
    if not isinstance(raw, dict):
        return {}
    return _normalize({str(k): float(v) for k, v in raw.items()})


def update_priors_from_episodes(
    existing: dict[str, Any],
    episodes: list[dict[str, Any]],
    lr: float = 0.5,
) -> dict[str, Any]:
    lr = min(1.0, max(0.01, float(lr)))
    by_wv_counts: dict[str, dict[str, dict[str, int]]] = {}

    for ep in episodes:
        if not ep.get("success"):
            continue
        workload = str(ep.get("workload_type", "UNKNOWN"))
        for step in ep.get("steps", []):
            view = str(step.get("view_pred", "UNKNOWN"))
            action = str(step.get("action", {}).get("type", "UNKNOWN"))
            by_wv_counts.setdefault(workload, {}).setdefault(view, {})
            by_wv_counts[workload][view][action] = by_wv_counts[workload][view].get(action, 0) + 1

    out = {"version": "1", "by_workload_view": dict(existing.get("by_workload_view", {}))}
    for workload, by_view in by_wv_counts.items():
        out["by_workload_view"].setdefault(workload, {})
        for view, counts in by_view.items():
            empirical = _normalize({k: float(v) for k, v in counts.items()})
            old = _normalize(out["by_workload_view"][workload].get(view, {}))
            keys = set(empirical) | set(old)
            blended = {k: (1.0 - lr) * old.get(k, 0.0) + lr * empirical.get(k, 0.0) for k in keys}
            out["by_workload_view"][workload][view] = _normalize(blended)
    return out


def blended_prior_prob(
    action_type: str,
    base_priors: dict[str, float],
    learned_priors: dict[str, float] | None = None,
) -> float:
    base = _normalize(base_priors)
    learned = _normalize(learned_priors or {})
    if learned:
        return 0.5 * base.get(action_type, 0.0) + 0.5 * learned.get(action_type, 0.0)
    return base.get(action_type, 0.0)


def score_action(
    action_type: str,
    base_priors: dict[str, float],
    learned_priors: dict[str, float] | None = None,
    alpha: float = 1.0,
) -> float:
    p = blended_prior_prob(action_type, base_priors, learned_priors)
    return float(alpha) * math.log(max(p, 1e-8))


def prune_candidates_by_prior(
    candidates: list[dict[str, Any]],
    base_priors: dict[str, float],
    learned_priors: dict[str, float] | None,
    top_k: int,
) -> list[dict[str, Any]]:
    if top_k <= 0 or len(candidates) <= top_k:
        return candidates
    ranked = sorted(
        candidates,
        key=lambda c: blended_prior_prob(str(c.get("type")), base_priors, learned_priors),
        reverse=True,
    )
    return ranked[:top_k]
