# computer-use-db-oracle

Research prototype for a workload- and schema-aware computer-use agent:

- Treat storefront UI as a state machine (`views` + `typed actions`)
- Treat agent behavior as planning over a UI capability graph
- Compare baseline free-form control vs state-aware + typed-action + priors

## Included In This Scaffold

- Execution plan: `docs/IMPLEMENTATION_PLAN.md`
- Repo blueprint: `docs/REPO_BLUEPRINT.md`
- Initial UI catalog: `agent/catalog/ui_catalog.yaml`
- Mongo task schema: `schemas/mongo/tasks.schema.json`
- Starter experiment config: `experiments/configs/exp_base.yaml`
- Starter task templates: `tasks/starter_20.json`
- Task materializer contract: `agent/src/agentlab/eval/materialize_tasks.py`
- Task materializer CLI: `agent/src/agentlab/cli/materialize_tasks.py`

## Immediate Next Steps

1. Stand up Mongo + minimal storefront (`HOME`, `SEARCH_RESULTS`, `PRODUCT_DETAIL`, `CART`)
2. Implement `view_classifier` and `state_extractors` against the catalog contract
3. Add task generator and oracle checker
4. Run ablation: `baseline`, `state_aware`, `typed_action`, `typed_action_priors`

## Materialize Starter Tasks

```bash
PYTHONPATH=agent/src python3 -m agentlab.cli.materialize_tasks \
  --templates tasks/starter_20.json \
  --products /path/to/products.sample.json \
  --out /tmp/materialized_tasks.json \
  --seed 42
```

## Download Item Metadata Subset

```bash
./scripts/download_amazon_reviews_2023_subset.sh
```

Downloaded files are stored in:
- `data/raw/amazon-reviews-2023/raw/meta_categories/`

## Ingest Item Metadata Into MongoDB

Dry-run parse/normalize:

```bash
PYTHONPATH=ingest/src python3 -m ingest.cli \
  --input 'data/raw/amazon-reviews-2023/raw/meta_categories/meta_*.jsonl' \
  --limit 1000 \
  --dry-run
```

Load into MongoDB (`pymongo` required):

```bash
PYTHONPATH=ingest/src python3 -m ingest.cli \
  --input 'data/raw/amazon-reviews-2023/raw/meta_categories/meta_*.jsonl' \
  --mongo-uri mongodb://localhost:27017 \
  --db simazon \
  --collection products \
  --batch-size 1000
```

## Build Facet Stats Artifact

```bash
.venv/bin/python scripts/build_facet_stats.py \
  --mongo-uri mongodb://localhost:27017 \
  --db simazon \
  --collection products \
  --top-k 50 \
  --out data/processed/facet_stats.json
```

## Run Original Prototype Loop

Single episode (typed actions + oracle verification):

```bash
PYTHONPATH=agent/src .venv/bin/python -m agentlab.cli.run_episode \
  --task-id T001 \
  --variant typed_action \
  --tasks-file tasks/starter_20.json \
  --catalog agent/catalog/ui_catalog.yaml \
  --mongo-uri mongodb://localhost:27017 \
  --db simazon \
  --collection products \
  --max-steps 30 \
  --out experiments/reports/episode_T001.json
```

Experiment matrix:

```bash
PYTHONPATH=agent/src .venv/bin/python -m agentlab.cli.run_experiment \
  --config experiments/configs/exp_base.yaml \
  --tasks-file tasks/starter_20.json \
  --catalog agent/catalog/ui_catalog.yaml \
  --mongo-uri mongodb://localhost:27017 \
  --db simazon \
  --collection products \
  --out experiments/reports/last_run.json
```

This also writes automatic rollups to:
- `experiments/reports/last_run.summary.json`

Screenshot-vs-path comparison run:

```bash
PYTHONPATH=agent/src .venv/bin/python -m agentlab.cli.run_experiment \
  --config experiments/configs/exp_screenshot_compare.yaml \
  --tasks-file tasks/starter_20.json \
  --catalog agent/catalog/ui_catalog.yaml \
  --mongo-uri mongodb://localhost:27017 \
  --db simazon \
  --collection products \
  --out experiments/reports/screenshot_compare.json
```

## Deploy Fake Storefront On Render

This repo includes a Render Blueprint at:
- `render.yaml`

Service:
- `simazon-ui-api` (FastAPI)
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Required env vars on Render:
- `MONGO_URI` (use MongoDB Atlas connection string)
- `MONGO_DB` (default `simazon`)

Deploy steps:
1. Push this repo to GitHub.
2. In Render, create a new Blueprint service from the repo.
3. Set `MONGO_URI` in Render dashboard.
4. Deploy.

Blueprint services included:
- `simazon-ui-api` (web app)
- `simazon-episode-worker` (episode generation worker)

After deploy:
- Fake storefront home: `/ui`
- Search: `/ui/search`
- Replay viewer: `/ui/replay?file=experiments/reports/last_run.json`

Notes:
- Replay viewer expects episode artifacts to be present under `experiments/artifacts` and JSON reports under `experiments/reports`.
- Render web instances are ephemeral; store long-lived reports/screenshots in object storage if needed.

Worker behavior:
- Script: `scripts/render_worker.py`
- Default mode: continuous loop every `JOB_INTERVAL_SECONDS` (default 1800s)
- Output reports: `experiments/reports/render/episodes_<timestamp>.json` and `.summary.json`
- Set `WORKER_MODE=once` to run a single generation cycle.
