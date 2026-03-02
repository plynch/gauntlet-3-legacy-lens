# LegacyLens Pre-Search Document

Patrick Lynch

March 2, 2026

This document completes the Phase 1-3 Pre-Search checklist from the project brief and locks architecture decisions for implementation.

## Project Constraints Snapshot

- Timeline: MVP due Tuesday, March 3, 2026 at 11:59 PM CT; Final due Wednesday, March 4, 2026 at 11:59 PM CT.
- Codebase target: GnuCOBOL.
- Deployment requirement: Publicly accessible browser experience for non-technical users.
- Stack direction: Python + FastAPI + React + Qdrant + OpenAI + Railway.
- Railway setup estimate: no more than 3 hours, given existing user familiarity with Railway from prior projects.
- Budget target: user-based monthly cost model (see Cost Analysis calculations below): about $53/month at 100 users, $357/month at 1,000 users, $3,278/month at 10,000 users, and $31,880/month at 100,000 users.
- Query-volume assumption for projections: 25 queries/user/day.

## Phase 1: Define Your Constraints

### 1. Scale & Load Profile

Decision:
- Build for at least 10,000+ LOC and 50+ files in GnuCOBOL.
- Target end-to-end query latency under 3 seconds.
- Assume 25 queries per user/day for production forecasting.
- Support incremental indexing from day one, plus full reindex fallback.

Rationale:
- Matches assignment minimums and gives a realistic retrieval workload.

Tradeoff:
- Incremental updates add complexity early.

Fallback:
- If incremental logic becomes unstable, run full reindex jobs while preserving query availability.

### 2. Budget & Cost Ceiling

Decision:
- Define budget ceilings by user tier (100, 1,000, 10,000, 100,000 users). (updated below)
- Track projected monthly cost in three buckets: embeddings, LLM generation, vector DB.
- Track effective cost per user/month and cost per query as primary budget metrics.
- Use the Cost Analysis calculations below as the baseline planning budget (not list pricing maximums).

Rationale:
- User-tier budgeting is directly aligned with real production scaling decisions.

Tradeoff:
- Forecast accuracy depends on query-volume and token-size assumptions.

Fallback:
- Recalculate budgets with conservative high-usage assumptions and cap token-heavy answer paths.

### 3. Time to Ship

Decision:
- Prioritize retrieval correctness before advanced features.
- MVP must include deployed browser app, semantic retrieval, cited snippets, relevance scores, and answer synthesis.
- Final delivery adds optimization and deeper evaluation.

Rationale:
- Tight timeline requires core-value-first delivery.

Tradeoff:
- Less time for UI polish and advanced capabilities in MVP.

Fallback:
- Keep UI simple but preserve strong retrieval and citation quality.

### 4. Data Sensitivity

Decision:
- Treat source code as open-source for this project.
- External APIs for embeddings and generation are allowed.
- No strict data residency constraints assumed.

Rationale:
- Enables fastest path with managed APIs.

Tradeoff:
- Increases dependency on third-party vendors.

Fallback:
- Keep provider interfaces modular so local/self-hosted options can replace hosted services later.

### 5. Team & Skill Constraints

Decision:
- Assume beginner-level RAG experience.
- Favor managed services and explicit, simple pipeline boundaries.

Rationale:
- Reduces operational risk in a compressed delivery window.

Tradeoff:
- Less control than full self-hosted infrastructure.

Fallback:
- Preserve abstraction layers around vector and model providers for later migration.

## Phase 2: Architecture Discovery

### 6. Vector Database Selection

Decision:
- Use Qdrant hosted on Railway.

Rationale:
- Keeps deployment on one platform, uses existing Railway credits, and provides vector-native search with metadata filtering and straightforward API usage.

Tradeoff:
- Self-hosted operations (resource sizing, backups, and upgrades) are our responsibility.

Fallback:
- Keep adapter layer so pgvector on Railway or a managed external vector database can be introduced if Qdrant performance/operations become a bottleneck.

### 7. Embedding Strategy

Decision:
- Use OpenAI embeddings for both ingestion and query encoding.
- Lock one embedding model per index version to maintain vector compatibility.
- Process embeddings in batches with retry/backoff.

Rationale:
- Simplifies implementation and consistency.

Tradeoff:
- API latency and rate limits can delay ingestion.

Fallback:
- Queue embedding jobs and cache by chunk hash to avoid duplicate embeds.

### 8. Chunking Approach

Decision:
- Use COBOL-aware chunk boundaries (PROGRAM-ID, SECTION, PARAGRAPH).
- Apply token-aware chunk caps with overlap.
- Store metadata: path, line ranges, symbol/section, hash.

Rationale:
- COBOL structure is semantically meaningful and improves retrieval relevance.

Tradeoff:
- Legacy formatting irregularities can reduce parser accuracy.

Fallback:
- Automatically switch low-confidence files to fixed-size overlap chunking.

### 9. Retrieval Pipeline

Decision:
- Embed query with the same model as ingestion.
- Run top-k vector search (initially k=8), then context-pack top results (default top 5 for synthesis).
- Use metadata filters when applicable.

Rationale:
- Balances recall and noise for a small-MVP retrieval system.

Tradeoff:
- Fixed k can under- or over-retrieve depending on query type.

Fallback:
- Add adaptive k and query normalization/expansion for ambiguous queries.

### 10. Answer Generation

Decision:
- Use OpenAI chat model for synthesis.
- Enforce grounded prompt policy: answer only from retrieved context.
- Require explicit citation formatting with file/line references.

Rationale:
- Citation-first outputs align with code-understanding and trust requirements.

Tradeoff:
- Strict grounding can produce shorter answers.

Fallback:
- Return "insufficient evidence" when retrieval context is weak rather than hallucinating.

### 11. Framework Selection

Decision:
- Backend: Python + FastAPI.
- Frontend: React.
- Orchestration: lightweight custom pipeline modules over heavy framework adoption in MVP.

Rationale:
- Keeps control simple and implementation fast.

Tradeoff:
- More hand-written orchestration code than framework-heavy approach.

Fallback:
- Introduce targeted framework components later if complexity increases.

## Phase 3: Post-Stack Refinement

### 12. Failure Mode Analysis

Expected failure modes:
- No relevant retrieval results.
- Ambiguous user queries.
- API rate limits/timeouts.
- Stale or partially updated index.
- Encoding or parsing anomalies in legacy files.

Handling strategy:
- Clear user-facing error states.
- Structured internal error logging with request IDs.
- Retry/backoff where safe.
- Full reindex option for index integrity recovery.

### 13. Evaluation Strategy

Decision:
- Build a labeled query set from assignment prompts and project-specific developer questions.
- Measure precision@5 for retrieval relevance.
- Track citation correctness (file/line accuracy).

Rationale:
- Retrieval quality is the core success metric of this project.

Tradeoff:
- Manual labeling effort under time pressure.

Fallback:
- Start with a smaller high-confidence labeled set and expand by Final deadline.

### 14. Performance Optimization

Decision:
- Cache file hashes and embeddings.
- Normalize query text before embedding.
- Tune retrieval parameters and trim prompt context to reduce latency/cost.

Rationale:
- Improves response speed and spend efficiency.

Tradeoff:
- Optimization can distract from correctness if done too early.

Fallback:
- Only keep optimizations that show measurable benefit without reducing retrieval precision.

### 15. Observability

Decision:
- Log request ID, latency, top chunk IDs/scores, token usage, and error categories.
- Track baseline metrics: p50/p95 latency, precision sample, error rate, spend trend.

Rationale:
- Required to debug retrieval failures quickly during short iterations.

Tradeoff:
- Adds implementation overhead during MVP.

Fallback:
- Start with structured logs and a simple metrics summary script.

### 16. Deployment & DevOps

Decision:
- Deploy backend, frontend, and Qdrant on Railway where possible.
- No-login browser access for MVP reviewers.
- Store API keys in Railway environment variables.
- Keep `.env` out of version control.

Rationale:
- Meets "deployed and publicly accessible" requirement directly.

Tradeoff:
- Single-platform deployment may constrain future scaling options.

Fallback:
- Split frontend/backend hosting post-MVP if scaling or reliability issues appear.

## Public Interfaces and Data Contracts

### Core Record Type

`ChunkRecord`:
- `id`
- `file_path`
- `start_line`
- `end_line`
- `symbol`
- `chunk_text`
- `hash`
- `updated_at`

### API Endpoints

- `POST /api/ingest/full`
- `POST /api/ingest/incremental`
- `POST /api/query`
- `GET /api/health`

### Query Response Contract

Response includes:
- `answer`
- `citations[]`
- `results[]` (snippet, score, metadata)
- `latency_ms`
- `warnings[]` (optional)

## Test Cases and Acceptance Scenarios

1. Public browser smoke test: open URL, submit query, receive answer with evidence.
2. Retrieval relevance: required assignment query categories return meaningful top-5 results.
3. Citation integrity: all citations map to valid file paths and line ranges.
4. Expandable context behavior: each result can reveal broader source context.
5. CLI/web parity: same query yields comparable evidence ranking and citations.
6. Incremental indexing: changed files update results without full reindex.
7. Failure handling: low-relevance retrieval triggers evidence-warning path.
8. Performance check: representative queries approach or stay under 3 seconds end-to-end.

## Cost Analysis Template

### User-Based Budget Targets (Assumption: 25 queries/user/day)

- 100 users: `$53/month` (`$0.53/user/month`)
- 1,000 users: `$357/month` (`$0.36/user/month`)
- 10,000 users: `$3,278/month` (`$0.33/user/month`)
- 100,000 users: `$31,880/month` (`$0.32/user/month`)

### Cost Inputs for Projection

- Embedding API cost: `$0.02 per 1M tokens` (text-embedding-3-small), estimated about `$0.47/month` at 1,000 users including incremental indexing.
- LLM generation cost: `$0.15 per 1M input tokens + $0.60 per 1M output tokens` (gpt-4o-mini), estimated about `$315/month` at 1,000 users.
- Vector DB hosting/usage: Railway resource pricing (`$10 per GB RAM/month`, `$20 per vCPU/month`, `$0.15 per GB volume/month`, plus plan minimum usage). Estimated Qdrant footprint at 1,000 users: about `2 GB RAM + 1 vCPU + 10 GB volume` = about `$42/month` resource usage.
- Average cost per query: `$0.00048` (blended estimate under assumptions below).

Assumptions to document during implementation:
- Average LLM usage per query: about `1,600` input tokens and `300` output tokens.
- Average query-embedding size: about `30` tokens/query.
- Average retrieved context size: sized to support the token profile above.
- Embedding volume for incremental code changes: about `1,000,000` tokens/month.
- Qdrant usage model at 1,000 users: about `2 GB RAM`, `1 vCPU`, `10 GB volume`, HNSW index on chunk embeddings, and metadata filtering on file/path/line fields.

## Final Notes

- Core principle: accurate retrieval with trustworthy citations is more important than complex architecture.
- MVP success is defined by usable public browser access and reliable evidence-backed answers.
