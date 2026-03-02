# Bootstrap Setup

## Local Development

1. Start services with Docker Compose.

```bash
docker compose up --build
```

2. Backend health endpoint should be available at `http://localhost:8000/api/health`.
3. Frontend runs at `http://localhost:4173` and calls backend health check on load.

If you prefer not to use Docker:

- Backend
  - `cd backend`
  - `pip install -r requirements.txt`
  - `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Frontend
  - `cd frontend`
  - `npm install`
  - `npm run dev`

## Railway First Deploy (Sub-PRD 00)

1. Create a Railway project and add three services:
   - qdrant (`qdrant/qdrant` image)
   - api (`backend` folder)
   - web (`frontend` folder)
2. For qdrant service:
   - keep it private (no public domain)
   - add a Railway Volume (at least 1GB) for persistence
3. Set API env vars:
   - `LEGACYLENS_QDRANT_URL` to private Railway qdrant URL
   - `LEGACYLENS_ALLOWED_ORIGINS` to `["https://<web-service>.up.railway.app"]`
   - `LEGACYLENS_OPENAI_API_KEY` for later integration
4. Set web env var:
   - `VITE_API_BASE_URL` to public api domain, e.g. `https://<api-service>.up.railway.app`
5. Deploy and open the web service domain in browser. You should see the shell and health status.

## Railway Environments (Dev + Production)

Use one of these approaches depending on your workflow.

### Option A: Two Railway Projects (simple and explicit)

1. Keep one git repo.
2. Create two Railway projects:
   - `legacylens-dev`
   - `legacylens-prod`
3. In each project, add `qdrant`, `api`, and `web` services.
4. Configure dev services with non-public test data and lighter settings.
5. Configure prod services for stable values and production secrets.
6. In prod, use your final data source and stronger `QDRANT` sizing/retention settings.

### Option B: One project with branch-based environments

1. Add all three services in one project.
2. Set `dev` or `develop` branch as the source for dev services.
3. Set `main` branch as the source for production services.
4. Maintain separate environment variables for each branch:
   - Dev API:
     - `LEGACYLENS_QDRANT_URL=<dev qdrant private URL>`
     - `LEGACYLENS_ALLOWED_ORIGINS=["https://<dev web domain>"]`
     - `VITE_API_BASE_URL=https://<dev api domain>`
   - Prod API:
     - `LEGACYLENS_QDRANT_URL=<prod qdrant private URL>`
     - `LEGACYLENS_ALLOWED_ORIGINS=["https://<prod web domain>"]`
     - `VITE_API_BASE_URL=https://<prod api domain>`
5. Keep API keys and any future paid keys in the corresponding environment only.

### Deployment checklist

1. Confirm API health endpoint is reachable in each environment.
2. Confirm web homepage loads in each environment.
3. Confirm service-to-service URLs in each environment match the target domain names.

## Railway Runbook: Staging and Production (same project)

### Initial identical deploy for both environments

1. Open the existing Railway project.
2. Switch environment selector to `staging`.
3. Add three services in staging:
4. `qdrant` service from image `qdrant/qdrant`.
5. Add a private storage volume to `qdrant` (at least 1GB).
6. `api` service from root `backend`.
7. `web` service from root `frontend`.
8. Use the existing default start commands from each service Dockerfile or `railway.toml`.
9. Copy these environment variables into staging:
10. `api`:
11. `LEGACYLENS_QDRANT_URL` points to staging qdrant private URL.
12. `LEGACYLENS_ALLOWED_ORIGINS` set to `["https://<staging-web-domain>"]`.
13. `LEGACYLENS_OPENAI_API_KEY` set when available.
14. `web`:
15. `VITE_API_BASE_URL` set to staging api public URL.
16. Trigger deploy for all three services and verify `https://<staging-web-domain>` loads health.
17. Open service settings for `api` and `web` and note the exact deployment branch/commit (usually `main` for now).
18. Switch environment selector to `production`.
19. Repeat steps 3-16 using the production domain URLs.
20. Confirm both environments now return working health on web and api endpoints.

### Promotion from staging to production

1. Use a single source of truth branch for staging and promote by commit to production branch.
2. Keep `staging` auto-deploying from `main` or your release branch.
3. Keep `production` manual deploy only or auto-deploy from `main`.
4. Promote by doing this sequence:
5. Verify staging.
6. Tag or merge the verified commit.
7. Deploy the exact same commit SHA to production.
8. Trigger production deployment from the matching commit in the Production deployment history.

### Automation path

1. Add required Railway tokens in GitHub as `RAILWAY_TOKEN`.
2. Use CI trigger on merge to staging branch:
3. `railway up` to `staging` environment.
4. Use manual workflow_dispatch for production that targets `production` environment.
5. Include a dry-run step before production deploy that opens both health URLs and checks `api/health` + web page.
6. Keep one commit SHA and use it for both environments to guarantee identity.

### Notes

1. Service URLs and allowed origins are environment-specific.
2. Qdrant data is not automatically shared between environments.
3. If you need production data to start clean, run the same ingest job in production after promotion.
