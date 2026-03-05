# Requirements Evidence Map

This maps each stated MVP hard-gate requirement to concrete evidence in the repo and deployed environments.

## MVP Hard-Gate Checklist

| Requirement | Status | Evidence |
| --- | --- | --- |
| Ingest at least one legacy codebase | met | Source corpus is [GnuCOBOL SourceForge trunk](https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/); ingest metrics in `docs/ingest-benchmarks.md`. |
| Chunk code files with syntax-aware splitting | met | COBOL chunking pipeline in `backend/app/services/cobol_chunker.py`; final architecture notes in `docs/rag-architecture-final.md`. |
| Generate embeddings for all chunks | met | Ingest stats show non-zero chunk counts (`8929`) after full ingest in staging/production (`docs/evaluation-results-staging.md`, `docs/evaluation-results-production.md`). |
| Store embeddings in a vector database | met | Qdrant gateway implementation in `backend/app/services/qdrant_gateway.py`; health shows Qdrant configured. |
| Implement semantic search across codebase | met | `POST /api/query` returns ranked evidence snippets and citations; sample results in `docs/evaluation-results-staging.md` and `docs/evaluation-results-production.md`. |
| Natural language query interface (CLI or web) | met | Public web UI on Railway frontend domains; query form and submit flow in `frontend/src/App.tsx`. |
| Return relevant code snippets with file/line references | met | Query response model includes `snippets` + `citations`; rendered in frontend with source links. |
| Basic answer generation using retrieved context | met | Query service composes final grounded answer with citation references (`backend/app/services/query_service.py`). |
| Deployed and publicly accessible | met | Public staging/production frontend + API domains documented in `docs/environments.md`. |

## Performance Target Evidence

Target from assignment:

- Ingestion throughput: `10,000+ LOC in <5 minutes`

Observed full-corpus runs:

1. Staging: `571,724 LOC` in `345.71s`
2. Production: `571,724 LOC` in `352.83s`

Both runs exceed the LOC target by a large factor while remaining in practical demo time.
