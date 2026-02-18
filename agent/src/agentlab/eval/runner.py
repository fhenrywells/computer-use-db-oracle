from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agentlab.control.baseline_freeform import next_action as baseline_next_action
from agentlab.control.screenshot_based import next_action as screenshot_next_action
from agentlab.control.state_aware import next_action as state_aware_next_action
from agentlab.control.typed_action import next_action as typed_next_action
from agentlab.control.vision_ocr import next_action as vision_ocr_next_action
from agentlab.eval.oracle import oracle_satisfied


def _pick_action(
    variant: str,
    task: dict[str, Any],
    observation: dict[str, Any],
    catalog: dict[str, Any],
    oracle_target_asin: str | None,
    learned_priors_model: dict[str, Any] | None,
) -> dict[str, Any]:
    if variant == "baseline_freeform":
        return baseline_next_action(task, observation)
    if variant == "screenshot_based":
        add_to_cart_count = int(sum(1 for s in observation.get("_history", []) if s.get("action", {}).get("type") == "AddToCart"))
        opened_related_count = int(
            sum(1 for s in observation.get("_history", []) if s.get("action", {}).get("type") == "OpenRelated")
        )
        visual_obs = {
            "view_id": observation.get("view_id"),
            "add_to_cart_count": add_to_cart_count,
            "opened_related_count": opened_related_count,
            "step_idx": observation.get("step_idx", 0),
            "screenshot_path": observation.get("screenshot_path"),
        }
        return screenshot_next_action(task, visual_obs)
    if variant == "vision_ocr":
        add_to_cart_count = int(sum(1 for s in observation.get("_history", []) if s.get("action", {}).get("type") == "AddToCart"))
        opened_related_count = int(
            sum(1 for s in observation.get("_history", []) if s.get("action", {}).get("type") == "OpenRelated")
        )
        visual_obs = {
            "view_id": observation.get("view_id"),
            "add_to_cart_count": add_to_cart_count,
            "opened_related_count": opened_related_count,
            "step_idx": observation.get("step_idx", 0),
            "screenshot_path": observation.get("screenshot_path"),
        }
        return vision_ocr_next_action(task, visual_obs)
    if variant == "state_aware":
        return state_aware_next_action(task, observation)
    if variant == "typed_action_priors":
        return typed_next_action(
            task,
            observation,
            catalog,
            oracle_target_asin=oracle_target_asin,
            use_priors=True,
            learned_priors_model=learned_priors_model,
        )
    return typed_next_action(
        task,
        observation,
        catalog,
        oracle_target_asin=oracle_target_asin,
        use_priors=False,
        learned_priors_model=learned_priors_model,
    )


def run_episode(
    env,
    task: dict[str, Any],
    variant: str,
    catalog: dict[str, Any],
    max_steps: int = 30,
    learned_priors_model: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = datetime.now(timezone.utc).isoformat()
    spec = task.get("spec", {})
    start_asin = spec.get("start_asin")
    edge = spec.get("edge") or spec.get("edge_used")
    observation = env.reset(start_asin=start_asin if isinstance(start_asin, str) else None, related_edge=edge if isinstance(edge, str) else None)
    target_asin = env.compute_oracle_target_asin(task)
    steps: list[dict[str, Any]] = []
    success = False
    steps_to_success: int | None = None

    for t in range(max_steps):
        # lightweight in-memory history exposed only to screenshot policy for step-local context.
        obs_for_policy = dict(observation)
        obs_for_policy["_history"] = steps
        action = _pick_action(variant, task, obs_for_policy, catalog, target_asin, learned_priors_model)
        if variant in {"screenshot_based", "vision_ocr"} and hasattr(env, "step"):
            next_obs, info = env.step(action, step_idx=t + 1)
        else:
            next_obs, info = env.step(action)
        done = oracle_satisfied(task, next_obs, expected_asin=target_asin)
        step = {
            "t": t,
            "view_pred": observation.get("view_id"),
            "action": action,
            "postcondition_ok": info.get("postcondition_ok", True),
            "event": info.get("event"),
            "state_vars": next_obs,
            "screenshot_path": info.get("screenshot_path"),
            "action_debug": action.get("_debug", {}),
            "oracle_done": done,
        }
        steps.append(step)
        observation = next_obs
        if done:
            success = True
            steps_to_success = t + 1
            break

    ended = datetime.now(timezone.utc).isoformat()
    return {
        "task_id": task.get("task_id"),
        "workload_type": task.get("workload_type"),
        "agent_variant": variant,
        "success": success,
        "steps_to_success": steps_to_success,
        "steps": steps,
        "oracle_target_asin": target_asin,
        "start_ts": started,
        "end_ts": ended,
    }
