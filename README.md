# LegacyLens

RAG application for understanding legacy COBOL code with grounded evidence.

## Implemented so far

- FastAPI backend with:
  - `GET /api/health`
  - `POST /api/ingest` (`mode=full|incremental`)
  - `POST /api/query`
- React frontend with:
  - Health status panel
  - "Index corpus" action
  - Query form with answer + citations + evidence snippets
- Qdrant vector storage integration
- Railway-ready deployment for staging and production

## Run locally

```bash
docker compose up --build
```

Then open:

- Frontend: `http://localhost:4173`
- API health: `http://localhost:8000/api/health`

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
