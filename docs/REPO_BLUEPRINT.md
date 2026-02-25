# Repo Blueprint

```text
db-oracle-agent-eval/
  README.md
  docker-compose.yml
  .env.example
  Makefile

  docs/
    IMPLEMENTATION_PLAN.md
    REPO_BLUEPRINT.md

  infra/
    mongo-init/
      init.js
    atlas/
      search-index.products.json
      vector-index.products.json

  data/
    raw/                     # gitignored
    processed/               # gitignored

  services/
    api/
      app/
        main.py
        settings.py
        routes/
          search.py
          products.py
          cart.py
          checkout.py
        db/
          mongo.py
          models.py
      tests/
    web/
      app/
        page.tsx
        search/page.tsx
        product/[asin]/page.tsx
        cart/page.tsx
        checkout/page.tsx
      components/
      lib/
      ui_perturbations/

  agent/
    catalog/
      ui_catalog.yaml
    src/agentlab/
      catalog/
      perception/
      control/
      env/
      eval/
      logging/
      cli/

  ingest/
    src/ingest/
      snap_amazon/
      enrich/

  experiments/
    configs/
      exp_base.yaml
      exp_perturbations.yaml
    notebooks/
    reports/

  schemas/
    mongo/
      products.schema.json
      tasks.schema.json
      episodes.schema.json
    ui_catalog.schema.json

  scripts/
    bootstrap.sh
    seed_demo.sh
```

## Interface Contracts

- `catalog`: `available_actions(view, state) -> TypedAction[]`
- `perception`: `classify_view(dom) -> (view_id, confidence)`
- `perception`: `extract_state_vars(dom, view_id) -> dict`
- `agent`: `next_action(task, observation) -> action`
- `oracle`: `check(task_materialized, final_state) -> success`
