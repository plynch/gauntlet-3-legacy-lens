# RAG Architecture Final

This document is the final architecture record for LegacyLens.

Scope:

1. Corpus: [GnuCOBOL SourceForge trunk](https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/).
2. App goal: answer codebase questions with grounded citations and evidence snippets.
3. Runtime: FastAPI API + React web client + Qdrant vector store on Railway.

## Vector DB Selection

Decision: `Qdrant` (hosted in Railway, private service + persistent volume).

Why:

1. Native dense-vector search with payload filtering.
2. Simple HTTP API (easy to keep custom RAG pipeline lightweight).
3. Good fit for metadata-heavy code chunks (path, line range, section, file hash, indexed_at).
4. Operationally simple in the current hosting stack (all core services in Railway).

Tradeoff:

1. We own ingestion orchestration and lifecycle logic directly (not hidden in framework defaults).
2. Advanced reranking/hybrid retrieval features are not enabled in MVP scope.

## Embedding Strategy

Decision: single embedding model for ingest and query (`text-embedding-3-small`).

Current behavior:

1. Ingestion embeds each chunk and stores vectors in Qdrant.
2. Query path embeds the user question with the same model.
3. Embedding calls are batched (`LEGACYLENS_EMBEDDING_BATCH_SIZE=24`) with retry/backoff for transient failures.

Degradation path:

1. If `LEGACYLENS_OPENAI_API_KEY` is unavailable, embeddings fall back to deterministic local hash embeddings.
2. This preserves app availability and reproducibility but may reduce semantic quality.

Why this strategy:

1. Same-model ingest/query keeps vector space aligned.
2. `text-embedding-3-small` kept costs low during repeated full ingests.
3. Fallback mode avoids total outage for demo and operational continuity.

## Chunking Strategy

Decision: COBOL-aware section chunking plus generic line-window fallback for non-COBOL files.

Implementation:

1. Detect COBOL paragraph/section anchors via `SECTION_PATTERN`.
2. Segment file by detected anchors.
3. If segment length <= `chunk_max_lines` (default `80`), emit one chunk.
4. If segment exceeds max size, emit overlapping windows (`chunk_overlap_lines`, default `16`).
5. If no COBOL anchors are found (common for C/C headers), chunk as overlapping fixed line windows.

Metadata captured per chunk:

1. `source_path`
2. `line_start`, `line_end`
3. `section`
4. `file_hash`
5. `indexed_at`

Why:

1. COBOL section boundaries are natural semantic units.
2. Line-window fallback keeps mixed-language corpus ingest robust under deadline.
3. Line-level metadata supports citation correctness requirements.

Current limitation:

1. C files are not yet function/AST-aware chunked; they use the line-window fallback.
2. Planned improvement after submission: extension-routed chunkers (for example C function-level chunking) while keeping this fallback for unknown file types.

## Retrieval Strategy

Decision: custom retrieve-then-generate pipeline (no heavy RAG framework in MVP).

Flow:

1. Embed question.
2. Qdrant top-k vector search (`LEGACYLENS_QUERY_TOP_K`, default `5`).
3. Build bounded context (`LEGACYLENS_MAX_CONTEXT_CHARACTERS`, default `9000`).
4. Generate answer with `gpt-4.1-mini` (or deterministic fallback when degraded).
5. Return:
   - answer text
   - citations (`path:start-end`)
   - evidence snippets + scores

Why:

1. Fast implementation under deadline, easy to reason about in interview.
2. Full control of citation format and failure behavior.
3. Lower operational overhead than introducing framework abstraction layers.

## Failure Modes and Degradation

Observed and handled failure modes:

1. OpenAI transport/API failures:
   - embedding retries with exponential backoff;
   - generation circuit breaker after repeated failures;
   - deterministic fallback answer path when degraded.
2. Missing source files at ingest time:
   - clear runtime error;
   - if prior index exists, message indicates existing corpus preserved.
3. Not-indexable files (for example effectively empty placeholders):
   - tracked separately as `files_not_indexable`;
   - reported in ingest stats instead of silent drop.
4. Redeploy state reset:
   - ingest status falls back to Qdrant persistence;
   - `last_indexed_at` now recovered from chunk payload metadata (`indexed_at`) when available.

Operational controls:

1. Staging keeps ingest controls enabled for testing.
2. Production can hide ingest controls (`VITE_ENABLE_INGEST_CONTROLS=false`) to reduce accidental reindex cost.

## Performance Results

Latest full-corpus ingest evidence (SourceForge trunk snapshot):

1. Corpus size: `418` files, `571,724` LOC.
2. Staging full ingest: `345.71s` (`~6.05s per 10k LOC`).
3. Production full ingest: `343.77s` (`~6.01s per 10k LOC` in latest recorded run; prior run `352.83s`).
4. Ingest target context: assignment target was `10,000+ LOC in <5 minutes`; LegacyLens ingests ~`57x` that LOC in ~`5.7` minutes.

Query evaluation (20-query labeled set):

1. Staging: p50 `3671.5 ms`, p95 `9996.3 ms`, mean precision@5 `0.410`, citation match `0.700`.
2. Production: p50 `4314.1 ms`, p95 `8644.3 ms`, mean precision@5 `0.410`, citation match `0.700`.

Evidence files:

1. `docs/evaluation-results-staging.md`
2. `docs/evaluation-results-production.md`
3. `docs/ingest-benchmarks.md`

## Final Architecture Notes

1. LegacyLens intentionally prioritizes transparent retrieval and citation grounding over framework complexity.
2. The architecture is modular enough to add reranking, hybrid retrieval, or AST-level chunking in future iterations without replacing core services.
