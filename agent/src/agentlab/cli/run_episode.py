import argparse
import json
import os
from pathlib import Path

from pymongo import MongoClient

from agentlab.catalog.loader import load_ui_catalog
from agentlab.control.priors import load_learned_priors
from agentlab.env.browser_playwright_env import BrowserPlaywrightEnv
from agentlab.env.simazon_env import SimazonEnv
from agentlab.eval.runner import run_episode
from agentlab.eval.task_resolver import resolve_task_template
from agentlab.eval.tasks import load_task_templates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    parser.add_argument(
        "--variant",
        default="typed_action",
        choices=["baseline_freeform", "state_aware", "typed_action", "typed_action_priors", "screenshot_based", "vision_ocr"],
    )
    parser.add_argument("--tasks-file", default="tasks/starter_20.json")
    parser.add_argument("--catalog", default="agent/catalog/ui_catalog.yaml")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db", default="simazon")
    parser.add_argument("--collection", default="products")
    parser.add_argument("--screenshot-base-url", default=os.getenv("SIMAZON_BASE_URL", ""))
    parser.add_argument("--learned-priors-path", default="agent/catalog/learned_priors.json")
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    templates = load_task_templates(args.tasks_file)
    selected = next((t for t in templates if t.get("task_id") == args.task_id), None)
    if not selected:
        raise ValueError(f"task_id {args.task_id} not found in {args.tasks_file}")

    client = MongoClient(args.mongo_uri)
    products_col = client[args.db][args.collection]
    try:
        task = resolve_task_template(selected, products_col, seed=args.seed)
    finally:
        client.close()

    catalog = load_ui_catalog(args.catalog)
    if args.variant in {"screenshot_based", "vision_ocr"}:
        if not args.screenshot_base_url:
            raise ValueError(f"{args.variant} requires --screenshot-base-url (e.g. https://<domain>)")
        env = BrowserPlaywrightEnv(args.screenshot_base_url)
    else:
        env = SimazonEnv(args.mongo_uri, db=args.db, collection=args.collection)
    learned_priors = load_learned_priors(args.learned_priors_path)
    try:
        episode = run_episode(
            env,
            task,
            args.variant,
            catalog,
            max_steps=args.max_steps,
            learned_priors_model=learned_priors,
        )
    finally:
        env.close()

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(episode, indent=2), encoding="utf-8")
        print(f"wrote episode to {out_path}")
    print(
        json.dumps(
            {
                "task_id": episode["task_id"],
                "variant": episode["agent_variant"],
                "success": episode["success"],
                "steps_to_success": episode["steps_to_success"],
                "oracle_target_asin": episode["oracle_target_asin"],
                "step_count": len(episode["steps"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
