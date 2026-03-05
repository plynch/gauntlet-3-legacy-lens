# LegacyLens

LegacyLens is a browser-based RAG app for understanding large legacy COBOL codebases with grounded evidence.

Primary corpus: [GnuCOBOL SourceForge trunk](https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/).

## Live Environments

1. Production frontend: [https://legacy-lens.up.railway.app/](https://legacy-lens.up.railway.app/)
2. Production API: [https://legacy-lens-api.up.railway.app/api/health](https://legacy-lens-api.up.railway.app/api/health)
3. Staging frontend: [https://legacy-lens-staging.up.railway.app/](https://legacy-lens-staging.up.railway.app/)
4. Staging API: [https://legacy-lens-api-staging.up.railway.app/api/health](https://legacy-lens-api-staging.up.railway.app/api/health)

## Demo Videos

1. MVP demo submission: [https://www.youtube.com/watch?v=SoYmpzqxb0g](https://www.youtube.com/watch?v=SoYmpzqxb0g)
2. Final demo submission: `TBD (to be added after recording today)`

## Key Documentation

1. [RAG Architecture Final](docs/rag-architecture-final.md)
2. [Requirements Evidence Map](docs/requirements-evidence-map.md)
3. [Evaluation Guide](docs/evaluation.md)
4. [Evaluation Results (Staging)](docs/evaluation-results-staging.md)
5. [Evaluation Results (Production)](docs/evaluation-results-production.md)
6. [Ingest Benchmarks](docs/ingest-benchmarks.md)
7. [Cost Analysis](docs/cost-analysis.md)
8. [Setup Guide](docs/setup.md)
9. [Railway Runbook](docs/railway-runbook.md)
10. [Environment URLs and Variables](docs/environments.md)
11. [Corpus Source Policy](docs/corpus-source.md)

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
2. Chunk source files with COBOL section anchors when present; otherwise use overlapping line-window fallback (used for most C files).
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
- demo query presets can prefill prompts (hide/show available)

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

## Latest Final Evidence Snapshot (March 4, 2026)

Source corpus: [GnuCOBOL SourceForge trunk](https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/)

| Environment | Health | Full ingest result | Corpus LOC | Duration |
| --- | --- | --- | ---: | ---: |
| staging | `ok` | `418 seen / 417 indexed / 1 not indexable` | 571724 | 345.71s |
| production | `ok` | `418 seen / 417 indexed / 1 not indexable` | 571724 | 343.77s |

Not-indexable file:

- `data/corpus/sourceforge-trunk/config/runtime_empty.cfg` (empty placeholder content)

Detailed evidence logs:

1. `docs/ingest-benchmarks.md`
2. `docs/evaluation-results-staging.md`
3. `docs/evaluation-results-production.md`

## API Endpoints

1. `GET /api/health`
2. `POST /api/corpus/sourceforge/sync`
3. `POST /api/corpus/sourceforge/full-ingest`
4. `POST /api/ingest?mode=full|incremental`
5. `GET /api/ingest/runs?limit=<n>`
6. `POST /api/query`
7. `GET /api/features`
8. `POST /api/features/{feature_key}/query`

`GET /api/health` now includes `openai_mode` (`openai` or `fallback`) and `degraded_reason` when circuit-breaker fallback is active.

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
4. Recommended cost-safe ops mode:
- staging keeps ingest controls enabled
- production disables ingest controls and uses scheduled ingest jobs

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
npm run test
npm run lint
npm run build
```

## Known Limits

1. C and non-COBOL files currently use overlapping line-window fallback chunking, not function/AST-aware chunking yet.
2. Incremental indexing marks unchanged files as `unchanged` by design (not a failure).
3. Some files may be reported as `not indexable` when they are effectively blank or cannot produce chunks; this is informational.
