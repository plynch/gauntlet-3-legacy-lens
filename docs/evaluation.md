# Evaluation Guide

## Purpose

Generate reproducible retrieval metrics (latency, precision@5, citation-match rate) for submission notes.

## Prerequisites

1. API is running locally or on staging.
2. Corpus is indexed (`POST /api/ingest`).

## Run

Run all commands from the repository root (`3-legacy-lens`) in a terminal.

Local API:

```bash
python3 scripts/eval/run_eval.py \
  --api-base http://localhost:8000 \
  --queries scripts/eval/queries.sample.json \
  --output-markdown docs/evaluation-results.md
```

Staging API:

```bash
python3 scripts/eval/run_eval.py \
  --api-base https://legacy-lens-api-staging.up.railway.app \
  --queries scripts/eval/queries.sample.json \
  --output-markdown docs/evaluation-results-staging.md
```

Production API:

```bash
python3 scripts/eval/run_eval.py \
  --api-base https://legacy-lens-api.up.railway.app \
  --queries scripts/eval/queries.sample.json \
  --output-markdown docs/evaluation-results-production.md
```

Quick check before running evaluation:

```bash
curl https://legacy-lens-api-staging.up.railway.app/api/health
curl https://legacy-lens-api.up.railway.app/api/health
```

## Output

`docs/evaluation-results.md` (whatever you specify after --output-markdown) includes:

1. p50 and p95 latency.
2. Mean precision@5.
3. Citation match rate.
4. Per-query breakdown table.

For live MVP demos, `docs/evaluation-results.md` also records:

1. Staging and production health check evidence.
2. Full-corpus ingest evidence (files, chunks, LOC, duration).
3. Representative query API evidence with citation paths.

## Query Spec Format

Each query JSON row supports:

1. `question` (required)
2. `expected_paths` (optional exact path matches)
3. `expected_path_contains` (optional path-fragment matches; recommended for SourceForge trunk snapshots)
