# LegacyLens Setup Guide

Canonical environment URLs live in `docs/environments.md`.
Canonical corpus source lives in `docs/corpus-source.md`.

## Local Setup (Docker)

1. Start services:

```bash
docker compose up --build
```

2. Open:
- Frontend: `http://localhost:4173`
- API health: `http://localhost:8000/api/health`

3. Sync latest GnuCOBOL SourceForge trunk snapshot:

```bash
./scripts/fetch-sourceforge-trunk.sh
```

4. Preferred: test ingest from browser first.

Open `http://localhost:4173` and click `Sync SourceForge + Reindex`.

5. Sync SourceForge trunk + full ingest via API (optional):

```bash
curl -X POST 'http://localhost:8000/api/corpus/sourceforge/full-ingest'
```

6. (Optional) direct ingest only:

```bash
curl -X POST 'http://localhost:8000/api/ingest?mode=full'
```

7. Query:

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

Recommended workflow:

1. Keep local `.env.staging` and `.env.production` files updated from templates.
2. When variables change, paste the relevant file contents into Railway service variables.
3. Treat Railway as runtime source of truth; keep templates in git for reproducibility.

Corpus workflow:

1. LegacyLens ingests only `data/corpus/sourceforge-trunk`.
2. Keep that directory synced from SourceForge trunk with `./scripts/fetch-sourceforge-trunk.sh`.

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
- `VITE_SOURCE_REPO_BASE_URL=https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk` (optional override; default already points to SourceForge trunk for clickable source links in UI)
- `VITE_ENABLE_INGEST_CONTROLS=true` (set to `false` for viewer-only environments where ingest should stay API/CLI-only)

## Deployment Gate

1. Merge feature work to `main`.
2. Verify staging web + API + query flow.
3. Promote by merging `main` into `production`.
4. Verify production web + API + query flow.
