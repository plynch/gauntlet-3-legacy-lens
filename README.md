# LegacyLens

LegacyLens is a browser-based RAG app for understanding large legacy COBOL codebases with grounded evidence.

## What This Is

1. A public web app where you ask questions about GnuCOBOL source code.
2. Answers are backed by retrieved code snippets and file/line citations.
3. Built for deadline-driven codebase onboarding and technical review demos.

## Who It Is For

1. Engineers onboarding to unfamiliar COBOL systems.
2. Reviewers evaluating retrieval quality and citation grounding.
3. Teams that need quick code understanding without IDE-heavy setup.

## When To Use It

Use LegacyLens when you need fast answers to questions like:

1. Where is file I/O performed?
2. Which sections modify a given record?
3. What does a paragraph/section do?
4. What evidence supports this answer?

Do not use it as a source-of-truth for code changes; it is a read/analyze tool.

## Source Of Truth Corpus

LegacyLens ingests only the latest GnuCOBOL SourceForge trunk:

- [GnuCOBOL SourceForge trunk](https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/)

Configured ingest directory:

- `data/corpus/sourceforge-trunk`

## How It Works

1. Sync SourceForge trunk into local/runtime corpus directory.
2. Chunk source files with section-aware boundaries and overlap fallback.
3. Embed chunks and store vectors + metadata in Qdrant.
4. On query, embed question, retrieve top-k chunks, generate grounded answer.
5. Return answer + citations + evidence snippets.

## Browser-First Staging Workflow (Recommended)

Use this first before CLI or curl checks.

1. Open staging frontend:
- `https://legacy-lens-staging.up.railway.app/`
2. Verify health panel shows `Status: ok`.
3. Click `Sync SourceForge + Reindex`.
4. Wait for ingest completion and verify UI shows:
- mode
- start time
- end time
- duration
- corpus LOC
- corpus size
5. Run at least 3 queries and verify:
- non-empty answer
- citations visible
- evidence snippets visible

Only after browser flow passes, run API checks if needed.

## API Endpoints

1. `GET /api/health`
2. `POST /api/corpus/sourceforge/sync`
3. `POST /api/corpus/sourceforge/full-ingest`
4. `POST /api/ingest?mode=full|incremental`
5. `GET /api/ingest/runs?limit=<n>`
6. `POST /api/query`
7. `GET /api/features`
8. `POST /api/features/{feature_key}/query`

## Local Run

```bash
docker compose up --build
```

Open:

1. Frontend: `http://localhost:4173`
2. API health: `http://localhost:8000/api/health`

Optional local corpus sync:

```bash
./scripts/fetch-sourceforge-trunk.sh
```

## Testing and Quality Checks

Backend:

```bash
docker compose run --rm -v "$PWD/backend:/app" api sh -lc \
  "pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt && PYTHONPATH=/app ruff check app tests && PYTHONPATH=/app pytest -q tests"
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run build
```

## Key Documentation

1. Architecture: `docs/architecture.md`
2. Setup: `docs/setup.md`
3. Railway runbook: `docs/railway-runbook.md`
4. Environment URLs/vars: `docs/environments.md`
5. Corpus source policy: `docs/corpus-source.md`
6. Evaluation guide: `docs/evaluation.md`
7. Ingest benchmarks: `docs/ingest-benchmarks.md`
8. Cost analysis: `docs/cost-analysis.md`
