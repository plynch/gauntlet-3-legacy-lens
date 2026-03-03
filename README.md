# LegacyLens

RAG application for understanding legacy COBOL code with grounded evidence.

## Implemented so far

- FastAPI backend with:
  - `GET /api/health`
  - `POST /api/corpus/sourceforge/full-ingest`
  - `POST /api/ingest` (`mode=full|incremental`)
  - `GET /api/ingest/runs`
  - `POST /api/query`
- React frontend with:
  - Health status panel
  - "Index changes" + "Reindex all" actions
  - Query form with answer + citations + evidence snippets
- Qdrant vector storage integration
- Railway-ready deployment for staging and production

## Key docs

1. Architecture: `docs/architecture.md`
2. Cost analysis: `docs/cost-analysis.md`
3. Environment URLs and vars: `docs/environments.md`
4. Railway runbook: `docs/railway-runbook.md`
5. Evaluation process: `docs/evaluation.md`
6. Ingest benchmarks: `docs/ingest-benchmarks.md`
7. Corpus source of truth: `docs/corpus-source.md`

## Run locally

```bash
docker compose up --build
```

Then open:

- Frontend: `http://localhost:4173`
- API health: `http://localhost:8000/api/health`

Sync latest GnuCOBOL trunk corpus before ingest:

```bash
./scripts/fetch-sourceforge-trunk.sh
```

## Testing and quality checks

Backend fast local loop (recommended for daily development):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -q tests
ruff check app tests
```

Backend Docker fallback (if you do not want local Python tooling):

```bash
docker compose run --rm -v "$PWD/backend:/app" api sh -lc \
  "pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt && PYTHONPATH=/app pytest -q tests"
```

Backend lint:

```bash
docker compose run --rm -v "$PWD/backend:/app" api sh -lc \
  "pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt && PYTHONPATH=/app ruff check app tests"
```

Fast targeted backend test (example):

```bash
docker compose run --rm -v "$PWD/backend:/app" api sh -lc \
  "pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt && PYTHONPATH=/app pytest -q tests/test_query_service.py"
```

Frontend checks:

```bash
cd frontend
npm ci
npm run lint
npm run build
```

## API quickstart

1. Sync SourceForge trunk + full ingest in one call:

```bash
curl -X POST 'http://localhost:8000/api/corpus/sourceforge/full-ingest'
```

2. (Optional) run direct ingest only:

```bash
curl -X POST 'http://localhost:8000/api/ingest?mode=full'
```

Every ingest response now includes benchmark telemetry (`started_at`, `completed_at`, `duration_seconds`, `corpus_loc`, `corpus_bytes`), and each run is appended to `backend/data/benchmarks/ingest_runs.jsonl` (or `data/benchmarks/ingest_runs.jsonl` in container runtime).

3. Ask a question:

```bash
curl -X POST 'http://localhost:8000/api/query' \
  -H 'Content-Type: application/json' \
  -d '{"question":"Where is file IO handled?"}'
```

4. Run a feature query:

```bash
curl -X POST 'http://localhost:8000/api/features/code_explanation/query' \
  -H 'Content-Type: application/json' \
  -d '{"subject":"READ-CUSTOMER"}'
```

Feature query endpoints are available for advanced workflows, but intentionally not shown in the default UI.

5. Review benchmark history:

```bash
curl 'http://localhost:8000/api/ingest/runs?limit=20'
```
