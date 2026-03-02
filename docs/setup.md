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
