import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone

import yaml
from pymongo import MongoClient

from agentlab.catalog.loader import load_ui_catalog
from agentlab.env.browser_playwright_env import BrowserPlaywrightEnv
from agentlab.env.simazon_env import SimazonEnv
from agentlab.eval.metrics import compute_rollups
from agentlab.eval.runner import run_episode
from agentlab.eval.task_resolver import resolve_task_template
from agentlab.eval.tasks import load_task_templates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--tasks-file", default="tasks/starter_20.json")
    parser.add_argument("--catalog", default="agent/catalog/ui_catalog.yaml")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db", default="simazon")
    parser.add_argument("--collection", default="products")
    parser.add_argument("--screenshot-base-url", default=os.getenv("SIMAZON_BASE_URL", ""))
    parser.add_argument("--out", default="experiments/reports/last_run.json")
    parser.add_argument("--summary-out", default="")
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    variants = cfg.get("variants", ["typed_action"])
    max_steps = int(cfg.get("max_steps_per_episode", 30))
    base_seed = int(cfg.get("seed", 42))

    tasks = load_task_templates(args.tasks_file)
    catalog = load_ui_catalog(args.catalog)

    results: list[dict] = []
    client = MongoClient(args.mongo_uri)
    products_col = client[args.db][args.collection]
    try:
        for idx, task_template in enumerate(tasks):
            task = resolve_task_template(task_template, products_col, seed=base_seed + idx)
            for variant in variants:
                if variant == "screenshot_based":
                    if not args.screenshot_base_url:
                        raise ValueError("screenshot_based variant requires --screenshot-base-url")
                    env = BrowserPlaywrightEnv(args.screenshot_base_url)
                else:
                    env = SimazonEnv(args.mongo_uri, db=args.db, collection=args.collection)
                try:
                    episode = run_episode(env, task, variant, catalog, max_steps=max_steps)
                finally:
                    env.close()
                results.append(episode)
    finally:
        client.close()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")

    rollups = compute_rollups(results)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": str(args.config),
        "episodes_file": str(out),
        "rollups": rollups,
    }
    if args.summary_out:
        summary_path = Path(args.summary_out)
    else:
        summary_path = out.with_suffix(".summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    total = len(results)
    successes = sum(1 for r in results if r.get("success"))
    print(
        json.dumps(
            {
                "episodes": total,
                "successes": successes,
                "success_rate": (successes / total) if total else 0.0,
                "out": str(out),
                "summary_out": str(summary_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
