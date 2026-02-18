from __future__ import annotations

import statistics
from collections import defaultdict


def invalid_action_rate(step_logs: list[dict]) -> float:
    if not step_logs:
        return 0.0
    invalid = sum(1 for s in step_logs if not s.get("postcondition_ok", True))
    return invalid / len(step_logs)


def thrash_score(step_logs: list[dict]) -> float:
    if not step_logs:
        return 0.0
    seen: dict[tuple[str, str], int] = {}
    for s in step_logs:
        view = str(s.get("view_pred", "UNKNOWN"))
        action_type = str(s.get("action", {}).get("type", "UNKNOWN"))
        key = (view, action_type)
        seen[key] = seen.get(key, 0) + 1
    repeats = sum((count - 1) for count in seen.values() if count > 1)
    return repeats / len(step_logs)


def _summary_for_group(episodes: list[dict]) -> dict:
    n = len(episodes)
    successes = [e for e in episodes if e.get("success")]
    success_rate = len(successes) / n if n else 0.0
    steps_success = [e.get("steps_to_success") for e in successes if isinstance(e.get("steps_to_success"), int)]
    median_steps = statistics.median(steps_success) if steps_success else None
    avg_invalid = sum(invalid_action_rate(e.get("steps", [])) for e in episodes) / n if n else 0.0
    avg_thrash = sum(thrash_score(e.get("steps", [])) for e in episodes) / n if n else 0.0
    return {
        "episodes": n,
        "successes": len(successes),
        "success_rate": round(success_rate, 4),
        "median_steps_to_success": median_steps,
        "avg_invalid_action_rate": round(avg_invalid, 4),
        "avg_thrash_score": round(avg_thrash, 4),
    }


def compute_rollups(episodes: list[dict]) -> dict:
    by_variant: dict[str, list[dict]] = defaultdict(list)
    by_workload: dict[str, list[dict]] = defaultdict(list)
    by_variant_workload: dict[tuple[str, str], list[dict]] = defaultdict(list)

    for ep in episodes:
        variant = str(ep.get("agent_variant", "UNKNOWN"))
        workload = str(ep.get("workload_type", "UNKNOWN"))
        by_variant[variant].append(ep)
        by_workload[workload].append(ep)
        by_variant_workload[(variant, workload)].append(ep)

    return {
        "overall": _summary_for_group(episodes),
        "by_variant": {k: _summary_for_group(v) for k, v in sorted(by_variant.items())},
        "by_workload": {k: _summary_for_group(v) for k, v in sorted(by_workload.items())},
        "by_variant_workload": {
            f"{variant}::{workload}": _summary_for_group(v)
            for (variant, workload), v in sorted(by_variant_workload.items())
        },
    }
