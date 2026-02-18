from __future__ import annotations

import statistics
import math
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
        "prior_effects": _prior_effects(episodes),
    }


def _js_divergence(p: dict[str, float], q: dict[str, float]) -> float:
    keys = set(p) | set(q)
    if not keys:
        return 0.0
    m = {k: 0.5 * p.get(k, 0.0) + 0.5 * q.get(k, 0.0) for k in keys}
    def kl(a: dict[str, float], b: dict[str, float]) -> float:
        s = 0.0
        for k in keys:
            av = a.get(k, 0.0)
            bv = b.get(k, 0.0)
            if av > 0 and bv > 0:
                s += av * math.log(av / bv)
        return s
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def _prior_effects(episodes: list[dict]) -> dict:
    by_task_variant: dict[tuple[str, str], dict] = {}
    for ep in episodes:
        key = (str(ep.get("task_id")), str(ep.get("agent_variant")))
        by_task_variant[key] = ep

    compared_steps = 0
    diverged_steps = 0
    dist_ta: dict[str, int] = {}
    dist_tp: dict[str, int] = {}

    task_ids = sorted({str(e.get("task_id")) for e in episodes})
    for tid in task_ids:
        ta = by_task_variant.get((tid, "typed_action"))
        tp = by_task_variant.get((tid, "typed_action_priors"))
        if not ta or not tp:
            continue
        steps_a = ta.get("steps", [])
        steps_p = tp.get("steps", [])
        for s in steps_a:
            a = str(s.get("action", {}).get("type", "UNKNOWN"))
            dist_ta[a] = dist_ta.get(a, 0) + 1
        for s in steps_p:
            a = str(s.get("action", {}).get("type", "UNKNOWN"))
            dist_tp[a] = dist_tp.get(a, 0) + 1
        for i in range(min(len(steps_a), len(steps_p))):
            compared_steps += 1
            a1 = str(steps_a[i].get("action", {}).get("type", "UNKNOWN"))
            a2 = str(steps_p[i].get("action", {}).get("type", "UNKNOWN"))
            if a1 != a2:
                diverged_steps += 1

    total_a = sum(dist_ta.values())
    total_p = sum(dist_tp.values())
    pa = {k: v / total_a for k, v in dist_ta.items()} if total_a else {}
    pp = {k: v / total_p for k, v in dist_tp.items()} if total_p else {}
    return {
        "compared_steps": compared_steps,
        "diverged_steps": diverged_steps,
        "action_choice_divergence_rate": round((diverged_steps / compared_steps), 4) if compared_steps else 0.0,
        "action_js_divergence": round(_js_divergence(pa, pp), 6),
    }
