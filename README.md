# LegacyLens

LegacyLens is a browser-based RAG app for understanding large legacy COBOL codebases with grounded evidence.

Primary corpus: [GnuCOBOL SourceForge trunk](https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/).

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

Expected upstream size (latest trunk snapshot during development):

1. Around `418` files.
2. Around `571,000+` LOC total.

## How It Works

1. Sync SourceForge trunk into local/runtime corpus directory.
2. Chunk source files with section-aware boundaries and overlap fallback.
3. Embed chunks and store vectors + metadata in Qdrant.
4. On query, embed question, retrieve top-k chunks, generate grounded answer.
5. Return answer + citations + evidence snippets.

## Example Queries (10)

1. Where is file I/O handled in this codebase?
2. What is the main entry point for `cobc`?
3. Which modules parse compiler command-line options?
4. Show error handling flow for failed file opens.
5. Where are copybooks resolved and loaded?
6. Which code paths create or modify symbol tables?
7. How does the runtime initialize before executing user code?
8. Find call sites related to numeric conversion routines.
9. What components interact with generated C output?
10. Show logging or diagnostics pathways used during compilation.

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

## MVP/Final Readiness Checklist

1. Public frontend is reachable in browser.
2. Health panel reports API `Status: ok`.
3. `Sync SourceForge + Reindex` completes successfully.
4. Ingest summary reports non-zero files, LOC, and chunks.
5. Query responses include:
- grounded answer text
- citations with file/line ranges
- evidence snippets
6. Staging verification is completed before production promotion.

## API Endpoints

1. `GET /api/health`
2. `POST /api/corpus/sourceforge/sync`
3. `POST /api/corpus/sourceforge/full-ingest`
4. `POST /api/ingest?mode=full|incremental`
5. `GET /api/ingest/runs?limit=<n>`
6. `POST /api/query`
7. `GET /api/features`
8. `POST /api/features/{feature_key}/query`

## Observability (Langfuse)

When `LEGACYLENS_LANGFUSE_BASE_URL`, `LEGACYLENS_LANGFUSE_PUBLIC_KEY`, and `LEGACYLENS_LANGFUSE_SECRET_KEY`
are configured on the API service, traces appear in Langfuse under:

1. `query.answer` (user query workflow)
2. `ingest.run` (indexing workflow)
3. `openai.embeddings` (embedding calls)
4. `openai.chat_completion` (answer generation calls)

## Deployment Model

1. Railway `staging` tracks `main`.
2. Railway `production` tracks `production`.
3. Promote only after manual staging smoke checks pass.

Detailed steps: `docs/railway-runbook.md`.

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

## Known Limits

1. Retrieval quality depends on chunking and embedding model behavior on mixed source/code assets.
2. Incremental indexing marks unchanged files as `unchanged` by design (not a failure).
3. Some files may be reported as `not indexable` when they are effectively blank or cannot produce chunks; this is informational.

## Key Documentation

1. Architecture: `docs/architecture.md`
2. Setup: `docs/setup.md`
3. Railway runbook: `docs/railway-runbook.md`
4. Environment URLs/vars: `docs/environments.md`
5. Corpus source policy: `docs/corpus-source.md`
6. Evaluation guide: `docs/evaluation.md`
7. Ingest benchmarks: `docs/ingest-benchmarks.md`
8. Cost analysis: `docs/cost-analysis.md`
