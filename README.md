# LegacyLens

RAG application for understanding legacy COBOL code with grounded evidence.

## Implemented so far

- FastAPI backend with:
  - `GET /api/health`
  - `POST /api/ingest` (`mode=full|incremental`)
  - `POST /api/query`
- React frontend with:
  - Health status panel
  - "Index changes" + "Reindex all" actions
  - Built-in code understanding feature runner (explanation, dependency mapping, pattern detection, business logic, error handling)
  - Query form with answer + citations + evidence snippets
- Qdrant vector storage integration
- Railway-ready deployment for staging and production

## Key docs

1. Architecture: `docs/architecture.md`
2. Cost analysis: `docs/cost-analysis.md`
3. Environment URLs and vars: `docs/environments.md`
4. Railway runbook: `docs/railway-runbook.md`
5. Evaluation process: `docs/evaluation.md`

## Run locally

```bash
docker compose up --build
```

Then open:

- Frontend: `http://localhost:4173`
- API health: `http://localhost:8000/api/health`

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

1. Index corpus:

```bash
curl -X POST 'http://localhost:8000/api/ingest?mode=full'
```

2. Ask a question:

```bash
curl -X POST 'http://localhost:8000/api/query' \
  -H 'Content-Type: application/json' \
  -d '{"question":"Where is file IO handled?"}'
```

3. Run a feature query:

```bash
curl -X POST 'http://localhost:8000/api/features/code_explanation/query' \
  -H 'Content-Type: application/json' \
  -d '{"subject":"READ-CUSTOMER"}'
```
