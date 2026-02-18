#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import os
import subprocess
import sys
import time
from pathlib import Path


def _utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_once() -> int:
    config = os.getenv("EXPERIMENT_CONFIG", "experiments/configs/exp_screenshot_compare.yaml")
    tasks = os.getenv("TASKS_FILE", "tasks/starter_20.json")
    catalog = os.getenv("CATALOG_FILE", "agent/catalog/ui_catalog.yaml")
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db = os.getenv("MONGO_DB", "simazon")
    collection = os.getenv("MONGO_COLLECTION", "products")
    out_dir = Path(os.getenv("REPORTS_DIR", "experiments/reports/render"))
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = _utc_stamp()
    out = out_dir / f"episodes_{stamp}.json"
    summary = out_dir / f"episodes_{stamp}.summary.json"

    cmd = [
        sys.executable,
        "-m",
        "agentlab.cli.run_experiment",
        "--config",
        config,
        "--tasks-file",
        tasks,
        "--catalog",
        catalog,
        "--mongo-uri",
        mongo_uri,
        "--db",
        mongo_db,
        "--collection",
        collection,
        "--out",
        str(out),
        "--summary-out",
        str(summary),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = "agent/src"
    print(f"[render-worker] running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, env=env, check=False)
    print(f"[render-worker] finished with code={proc.returncode} out={out} summary={summary}")
    return proc.returncode


def main() -> None:
    run_mode = os.getenv("WORKER_MODE", "loop").lower()
    interval_s = int(os.getenv("JOB_INTERVAL_SECONDS", "1800"))

    if run_mode == "once":
        code = run_once()
        raise SystemExit(code)

    while True:
        run_once()
        print(f"[render-worker] sleeping {interval_s}s")
        time.sleep(max(30, interval_s))


if __name__ == "__main__":
    main()
