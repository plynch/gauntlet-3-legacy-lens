# Railway Runbook

Canonical environment URLs live in `docs/environments.md`.
Canonical corpus source lives in `docs/corpus-source.md`.

## Environment Strategy

1. One Railway project with two environments:
- `staging` tracks `main`
- `production` tracks `production`
2. Same service topology in both:
- `qdrant` (private + persistent volume)
- `api`
- `frontend`

## First-Time Setup per Environment

1. Create services:
- `qdrant` from image `qdrant/qdrant:latest`
- `api` from repo root directory `/backend`
- `frontend` from repo root directory `/frontend`
2. Add qdrant volume mounted at `/qdrant/storage`.
3. Generate public domains for `api` and `frontend`.
4. Keep qdrant private (no public domain).

## Variables

API service:

```env
LEGACYLENS_APP_NAME=LegacyLens API (<Environment>)
LEGACYLENS_ENVIRONMENT=<staging|production>
LEGACYLENS_API_PREFIX=/api
LEGACYLENS_API_VERSION=0.1.0
LEGACYLENS_ALLOWED_ORIGINS=["https://<frontend-domain>"]
LEGACYLENS_QDRANT_URL=http://qdrant.railway.internal:6333
LEGACYLENS_QDRANT_COLLECTION=legacylens_chunks
LEGACYLENS_OPENAI_API_KEY=<secret>
LEGACYLENS_LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
LEGACYLENS_LANGFUSE_PUBLIC_KEY=<secret>
LEGACYLENS_LANGFUSE_SECRET_KEY=<secret>
LEGACYLENS_EMBEDDING_MODEL=text-embedding-3-small
LEGACYLENS_GENERATION_MODEL=gpt-4.1-mini
LEGACYLENS_QUERY_TOP_K=5
LEGACYLENS_MAX_CONTEXT_CHARACTERS=9000
LEGACYLENS_SOURCE_DIRECTORIES=["data/corpus/sourceforge-trunk"]
LEGACYLENS_SOURCE_EXTENSIONS=[]
LEGACYLENS_CHUNK_MAX_LINES=80
LEGACYLENS_CHUNK_OVERLAP_LINES=16
LEGACYLENS_SOURCEFORGE_SYNC_TIMEOUT_SECONDS=120
```

## Corpus Source Policy

1. Ingest target is only SourceForge GnuCOBOL trunk:
- `https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/`
2. Keep `backend/data/corpus/sourceforge-trunk` synced before deploy:
- `./scripts/fetch-sourceforge-trunk.sh`

Frontend service:

```env
VITE_API_BASE_URL=https://<api-domain>
VITE_SOURCE_REPO_BASE_URL=https://github.com/<org-or-user>/<repo>/blob/<branch>
```

## Smoke Test Checklist

1. Open frontend URL and verify health panel returns `Status: ok`.
2. In browser, click `Sync SourceForge + Reindex` first.
3. Confirm ingest summary shows timing + corpus metrics in UI.
4. In browser, run at least 3 queries.
5. Confirm each response includes:
- non-empty `answer`
- `citations`
- `snippets`
6. Optional API verification:
- `POST https://<api-domain>/api/corpus/sourceforge/full-ingest`
- `GET https://<api-domain>/api/ingest/runs?limit=5`
- `POST https://<api-domain>/api/query`

## Promotion Procedure

1. Merge feature branch into `main`.
2. Confirm staging smoke checks pass.
3. Merge `main` into `production`.
4. Wait for production deploy and repeat smoke checks.
5. If production fails, redeploy previous known-good deployment from Railway history.

## Automation

1. Primary deployment mechanism: Railway native GitHub integration per environment/service.
2. Staging deploys automatically from `main` via Railway.
3. Production deploys automatically from `production` via Railway.
4. No GitHub Actions workflows are required for deployment in this project.
