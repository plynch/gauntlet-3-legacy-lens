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
