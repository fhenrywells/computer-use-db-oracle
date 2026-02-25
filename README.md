# db-oracle-agent-eval

Research prototype for evaluating shopping agents on a simulated storefront.

## What This Repo Does

- Hosts a fake Amazon-like UI (`/ui`, `/ui/search`, `/ui/product`, `/ui/cart`)
- Runs batch experiment jobs over shopping tasks
- Compares policy families under identical conditions
- Logs episodes and computes rollups (success rate, steps, invalid actions, thrash)
- Provides replay UI to inspect step-by-step behavior and screenshots

## Policy Buckets

`structured path-aware control`:
- `baseline_freeform`: weak unguided baseline
- `state_aware`: uses inferred view/state features
- `typed_action`: uses view-constrained typed actions and task scoring
- `typed_action_priors`: typed actions + learned priors from successful runs

`visual/screenshot-driven control`:
- `screenshot_based`: decisions from screenshot-derived cues
- `vision_ocr`: screenshot + OCR interpretation

## Agent Lifecycle (Per Episode)

1. Load a task (for example: exact SKU, cheapest under constraints, related-item browse)
2. Reset environment to task start state
3. Observe current state
4. Policy chooses next action
5. Execute action in UI
6. Re-observe, log step, and check oracle success
7. Repeat until success or step cap

## User Workflow (curl only)

All user-facing actions are API calls to your deployed Render service.

Set variables:

```bash
export BASE="https://<your-render-domain>"
export ADMIN_TOKEN="<your_admin_token>"
export MONGO_URI="mongodb+srv://<user>:<pass>@<cluster>/?appName=Cluster0"
```

Submit heavy suite (`exp_heavy.yaml`):

```bash
curl -s -X POST "$BASE/admin/run-experiment" \
  -H "Content-Type: application/json" \
  -H "x-admin-token: $ADMIN_TOKEN" \
  -d "{
    \"config\":\"experiments/configs/exp_heavy.yaml\",
    \"tasks_file\":\"tasks/starter_20.json\",
    \"catalog\":\"agent/catalog/ui_catalog.yaml\",
    \"mongo_uri\":\"$MONGO_URI\",
    \"mongo_db\":\"simazon\",
    \"collection\":\"products\",
    \"screenshot_base_url\":\"$BASE\"
  }"
```

Observe progress (poll by `job_id`):

```bash
curl -s -H "x-admin-token: $ADMIN_TOKEN" "$BASE/admin/jobs/<job_id>"
```

Inspect results when job finishes:

```bash
curl -s -H "x-admin-token: $ADMIN_TOKEN" "$BASE/admin/jobs/<job_id>"
```

Read these fields from the job JSON:
- `status`
- `replay_url` (open in browser)
- `out` (episodes file path)
- `summary_out` (rollups file path)

## Notes

- `screenshot_base_url` should usually be your API base URL (same as `$BASE`).
- Replay serves screenshots from `/artifacts/<filename>`.
- If `/admin/jobs/<job_id>` returns 404 during long runs, job state was likely lost across restart (current admin job store is in-memory).
- Sample heavy-run rollups are checked in at `docs/results/exp_heavy_sample_2026-02-24.summary.json`.
