# Railway Deployment and Promotion Runbook

This runbook assumes one Railway project with two environments:

1. `staging`
2. `production`

Both environments run the same three services:

1. `qdrant`
2. `api`
3. `web`

## 1. Prerequisites

1. Push this repo to GitHub first.
2. Railway project already exists with `staging` and `production` environments.
3. You have Railway service domains enabled for `api` and `web` in each environment.

## 1.1 Environment file templates in this repo

1. Backend staging: `backend/.env.staging.example`
2. Backend production: `backend/.env.production.example`
3. Frontend staging: `frontend/.env.staging.example`
4. Frontend production: `frontend/.env.production.example`
5. To generate local `.env` files from those templates, run:
6. `./scripts/sync-env-files.sh`
7. Generated `.env` files are gitignored and safe to edit locally.

## 2. First-time setup in Railway (staging)

1. In Railway, select the `staging` environment.
2. Create service `qdrant` from Docker image `qdrant/qdrant:latest`.
3. Add a volume to `qdrant` mounted at `/qdrant/storage` (at least 1 GB).
4. Create service `api` from GitHub repo.
5. Set `api` root directory to `backend`.
6. Create service `web` from GitHub repo.
7. Set `web` root directory to `frontend`.
8. Generate public domains for `api` and `web`.
9. Keep `qdrant` private.

Set environment variables in `staging`:

1. `api`
2. `LEGACYLENS_QDRANT_URL=http://qdrant.railway.internal:6333`
3. `LEGACYLENS_ALLOWED_ORIGINS=["https://<staging-web-domain>"]`
4. `LEGACYLENS_OPENAI_API_KEY=<your key>`
5. `web`
6. `VITE_API_BASE_URL=https://<staging-api-domain>`

Deploy staging and verify:

1. `https://<staging-api-domain>/api/health`
2. `https://<staging-web-domain>`

## 3. Mirror setup in Railway (production)

1. Switch environment to `production`.
2. Create the same service names: `qdrant`, `api`, `web`.
3. Configure roots the same way (`backend` for `api`, `frontend` for `web`).
4. Add qdrant volume at `/qdrant/storage`.
5. Generate production domains for `api` and `web`.
6. Set production environment variables:
7. `api`
8. `LEGACYLENS_QDRANT_URL=http://qdrant.railway.internal:6333`
9. `LEGACYLENS_ALLOWED_ORIGINS=["https://<production-web-domain>"]`
10. `LEGACYLENS_OPENAI_API_KEY=<your key>`
11. `web`
12. `VITE_API_BASE_URL=https://<production-api-domain>`

## 4. GitHub automation setup

This repo includes two workflows:

1. `.github/workflows/railway-deploy-staging.yml`
2. `.github/workflows/railway-promote-production.yml`

Add these GitHub repository secrets:

1. `RAILWAY_PROJECT_ID` (same Railway project id)
2. `RAILWAY_STAGING_TOKEN` (project token scoped to staging)
3. `RAILWAY_PRODUCTION_TOKEN` (project token scoped to production)
4. `STAGING_API_HEALTH_URL` (full url, usually `https://.../api/health`)
5. `STAGING_WEB_URL` (full web url)
6. `PRODUCTION_API_HEALTH_URL` (full url, usually `https://.../api/health`)
7. `PRODUCTION_WEB_URL` (full web url)

Recommended branch strategy:

1. `main` deploys to staging automatically via `railway-deploy-staging.yml`.
2. Production deploy is manual via `railway-promote-production.yml`.

## 5. Promote staging to production

1. Pick a commit SHA that is already healthy in staging.
2. In GitHub, open Actions.
3. Run `Promote Staging Commit to Production (Railway)`.
4. Paste the exact `commit_sha`.
5. Wait for production smoke checks to pass.

## 6. Rollback

1. In Railway production environment, open `api` or `web` service.
2. Open Deployments.
3. Redeploy the previous successful deployment.
4. Re-check:
5. `https://<production-api-domain>/api/health`
6. `https://<production-web-domain>`

## 7. Notes and constraints

1. Staging and production qdrant data are separate.
2. Promotion deploys app code, not qdrant dataset state.
3. If production data is missing, run ingest in production after deploy.
