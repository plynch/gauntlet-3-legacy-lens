# LegacyLens

Repository scaffold for an MVP-friendly RAG application.

## Current scope

This branch implements Sub-PRD 00 (bootstrap and first deploy):

- FastAPI backend with `/api/health`
- React shell with backend health binding
- Local dev stack with Docker Compose (`qdrant`, `api`, `web`)
- Deployment-ready structure for Railway

Run local:

```bash
docker compose up --build
```

Then open `http://localhost:4173`.
