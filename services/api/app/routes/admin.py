from __future__ import annotations

import datetime as dt
import os
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])

_JOBS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()


class RunExperimentRequest(BaseModel):
    config: str = "experiments/configs/exp_base.yaml"
    tasks_file: str = "tasks/starter_20.json"
    catalog: str = "agent/catalog/ui_catalog.yaml"
    mongo_uri: str | None = None
    mongo_db: str | None = None
    collection: str = "products"
    screenshot_base_url: str | None = None
    max_steps: int | None = None


def _repo_root() -> Path:
    # .../services/api/app/routes/admin.py -> repo root at parents[4]
    return Path(__file__).resolve().parents[4]


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _require_admin(request: Request) -> None:
    expected = os.getenv("ADMIN_TOKEN", "").strip()
    if not expected:
        return

    token = request.headers.get("x-admin-token", "").strip()
    auth = request.headers.get("authorization", "").strip()
    if not token and auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    if token != expected:
        raise HTTPException(status_code=401, detail="invalid admin token")


def _run_job(job_id: str, payload: RunExperimentRequest) -> None:
    root = _repo_root()
    with _LOCK:
        out = Path(_JOBS[job_id]["out"])
        summary = Path(_JOBS[job_id]["summary_out"])

    cmd = [
        sys.executable,
        "-m",
        "agentlab.cli.run_experiment",
        "--config",
        str(root / payload.config),
        "--tasks-file",
        str(root / payload.tasks_file),
        "--catalog",
        str(root / payload.catalog),
        "--mongo-uri",
        payload.mongo_uri or os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        "--db",
        payload.mongo_db or os.getenv("MONGO_DB", "simazon"),
        "--collection",
        payload.collection,
        "--screenshot-base-url",
        payload.screenshot_base_url or os.getenv("SIMAZON_BASE_URL", ""),
        "--out",
        str(out),
        "--summary-out",
        str(summary),
    ]
    if payload.max_steps is not None:
        # optional override via temp config is skipped for simplicity; keep contract stable.
        pass

    with _LOCK:
        _JOBS[job_id]["status"] = "running"
        _JOBS[job_id]["started_at"] = _now()
        _JOBS[job_id]["command"] = cmd

    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "agent" / "src")
    proc = subprocess.run(cmd, env=env, cwd=str(root), capture_output=True, text=True)

    with _LOCK:
        _JOBS[job_id]["status"] = "succeeded" if proc.returncode == 0 else "failed"
        _JOBS[job_id]["finished_at"] = _now()
        _JOBS[job_id]["returncode"] = proc.returncode
        _JOBS[job_id]["stdout_tail"] = (proc.stdout or "")[-4000:]
        _JOBS[job_id]["stderr_tail"] = (proc.stderr or "")[-4000:]


@router.post("/run-experiment")
def run_experiment(payload: RunExperimentRequest, request: Request):
    _require_admin(request)
    job_id = uuid.uuid4().hex[:12]
    root = _repo_root()
    reports_dir = root / "experiments" / "reports" / "admin"
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = reports_dir / f"{job_id}_{stamp}.json"
    summary = reports_dir / f"{job_id}_{stamp}.summary.json"
    with _LOCK:
        _JOBS[job_id] = {
            "id": job_id,
            "status": "queued",
            "created_at": _now(),
            "payload": payload.model_dump(),
            "out": str(out),
            "summary_out": str(summary),
            "replay_url": f"/ui/replay?file={out}",
        }
    t = threading.Thread(target=_run_job, args=(job_id, payload), daemon=True)
    t.start()
    return {"job_id": job_id, "status": "queued", "check_url": f"/admin/jobs/{job_id}"}


@router.get("/jobs")
def list_jobs(request: Request):
    _require_admin(request)
    with _LOCK:
        return {"jobs": list(_JOBS.values())}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request):
    _require_admin(request)
    with _LOCK:
        job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job
