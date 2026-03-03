# Evaluation Guide

## Purpose

Generate reproducible retrieval metrics (latency, precision@5, citation-match rate) for submission notes.

## Prerequisites

1. API is running locally or on staging.
2. Corpus is indexed (`POST /api/ingest`).

## Run

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
  --api-base https://<staging-api-domain> \
  --queries scripts/eval/queries.sample.json \
  --output-markdown docs/evaluation-results.md
```

## Output

`docs/evaluation-results.md` includes:

1. p50 and p95 latency.
2. Mean precision@5.
3. Citation match rate.
4. Per-query breakdown table.
