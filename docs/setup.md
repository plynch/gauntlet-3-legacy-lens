# LegacyLens Setup Guide

## Local Setup (Docker)

1. Start services:

```bash
docker compose up --build
```

2. Open:
- Frontend: `http://localhost:4173`
- API health: `http://localhost:8000/api/health`

3. Index the local sample corpus:

```bash
curl -X POST 'http://localhost:8000/api/ingest?mode=full'
```

4. Query:

```bash
curl -X POST 'http://localhost:8000/api/query' \
  -H 'Content-Type: application/json' \
  -d '{"question":"Where is file IO handled?"}'
```

## Local Setup (without Docker)

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

Backend templates:
- `backend/.env.example`
- `backend/.env.staging.example`
- `backend/.env.production.example`

Frontend templates:
- `frontend/.env.staging.example`
- `frontend/.env.production.example`

Generate local `.env` files from templates:

```bash
./scripts/sync-env-files.sh
```

## Railway Setup

One Railway project, two environments:

1. `staging` (tracks `main`)
2. `production` (tracks `production`)

Each environment has three services:

1. `qdrant` (private, with volume mounted at `/qdrant/storage`)
2. `api` (root directory `/backend`)
3. `frontend` (root directory `/frontend`)

Required variables:

1. API service:
- `LEGACYLENS_QDRANT_URL=http://qdrant.railway.internal:6333`
- `LEGACYLENS_ALLOWED_ORIGINS=["https://<web-domain>"]`
- `LEGACYLENS_OPENAI_API_KEY=<secret>` (optional but recommended for generated synthesis)
2. Frontend service:
- `VITE_API_BASE_URL=https://<api-domain>`

## Deployment Gate

1. Merge feature work to `main`.
2. Verify staging web + API + query flow.
3. Promote by merging `main` into `production`.
4. Verify production web + API + query flow.
