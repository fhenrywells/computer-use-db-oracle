# Implementation Plan

## Milestone 0: Foundations

- Define invariants:
  - deterministic selectors (`data-testid`)
  - explicit `view-id` marker
  - oracle-based success from DB state
- Standardize run metadata:
  - `agent_variant`
  - `catalog_version`
  - `ui_perturbation_version`
- Deliverables:
  - `docker-compose.yml` (Mongo + API + web + runner)
  - shared config for Mongo URI, dataset paths, run defaults

## Milestone 1: Catalog Ingestion (MongoDB)

- Ingest SNAP subset into `products`
- Normalize facet/search fields (`brand`, `category_leaf`, `price`, `rating_*`)
- Create indexes:
  - `products.asin` unique
  - facet and sort fields
- Deliverables:
  - `ingest` scripts: download, parse, normalize, load
  - search index specs checked into repo

## Milestone 2: Simulated Storefront

- Implement views:
  - `HOME`
  - `SEARCH_RESULTS`
  - `PRODUCT_DETAIL`
  - `CART`
  - `CHECKOUT` (minimal)
- Implement actions:
  - search, facet, sort, open result, add to cart, quantity changes
- Deliverables:
  - stable URL model
  - API endpoints for search/product/cart/checkout

## Milestone 3: UI Catalog + Perception Layer

- Implement `ui_catalog` contract:
  - state vars per view
  - typed actions
  - pre/postconditions
  - priors
- Implement:
  - `classify_view(dom) -> view_id, confidence`
  - `extract_state_vars(dom, view_id) -> vars`
- Deliverables:
  - versioned `ui_catalog.yaml`
  - deterministic classifier first, learned fallback later

## Milestone 4: Agent Variants + Harness

- Implement variants:
  - `baseline_freeform`
  - `state_aware`
  - `typed_action`
  - `typed_action_priors`
- Instrument each step:
  - predicted/true view
  - action
  - postcondition success
  - state vars
  - reward/progress markers
- Deliverables:
  - episode runner + step logger into Mongo
  - reproducible seeding

## Milestone 5: Tasks + Oracles

- Workloads:
  - cheapest under constraints
  - highest rated by brand/category
  - exact SKU
  - related-product traversal
- Deliverables:
  - task generator
  - oracle resolver from Mongo-only logic

## Milestone 6: Experiment + Analysis

- Batch-run matrix by variant + perturbation profile
- Metrics:
  - success
  - steps-to-success
  - invalid-action rate
  - thrash score
  - view misclassification rate
  - regret vs oracle length
- Deliverables:
  - experiment runner CLI
  - analysis notebook + figures + concise report

## Milestone 7: Robustness via UI Perturbations

- Add controlled UI changes:
  - facet reorder
  - label renames
  - hide testids
  - sponsored blocks
  - pagination/infinite-scroll toggle
- Re-run matrix and compare degradation curves
- Deliverables:
  - perturbation presets
  - robustness plots by variant
