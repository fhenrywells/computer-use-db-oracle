from typing import Any


def pick_best_action(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not candidates:
        return {"type": "NoOp", "args": {}}
    ranked = sorted(candidates, key=lambda c: float(c.get("score", 0.0)), reverse=True)
    best = ranked[0].copy()
    best.pop("score", None)
    return best
