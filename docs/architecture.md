# LegacyLens Architecture

## System Overview

LegacyLens is a staging-first RAG application for legacy COBOL code understanding.

1. Frontend (`React + TypeScript`) provides:
- health check
- ingest controls (`Index changes`, `Reindex all`)
- free-form query UI with citations and snippets
2. Backend (`FastAPI`) provides:
- `GET /api/health`
- `GET /api/features`
- `POST /api/features/{feature_key}/query`
- `POST /api/query`
- `POST /api/ingest?mode=full|incremental`
3. Vector store (`Qdrant`) stores chunk vectors + metadata.

## Request Flow

## Ingestion

1. Discover source files by configured directories and extensions.
2. Load/normalize source text.
3. COBOL chunking emits chunk text + metadata (path, line range, section).
4. Embedding generation:
- OpenAI embeddings when key exists
- deterministic local fallback when key is absent
5. Upsert points into Qdrant.
6. Incremental mode skips unchanged files via hash match.

## Query

1. User asks a free-form question.
2. Backend embeds the question and performs retrieval.
3. Embed question with the same embedding model.
4. Retrieve top-k nearest chunks from Qdrant.
5. Generate grounded answer from retrieved context.
6. Return answer with citations and snippets.

## Optional Feature APIs

Current explicit code-understanding features:

1. `code_explanation`
2. `dependency_mapping`
3. `pattern_detection`
4. `business_logic_extraction`
5. `error_handling_review`

Each feature is a stable query template over the same retrieval/synthesis pipeline.
These APIs are available for advanced workflows and evaluation, but not exposed in the default staging UI.

## Deployment Topology

Single Railway project with two environments:

1. `staging` tracks `main`
2. `production` tracks `production`

Per environment services:

1. `frontend`
2. `api`
3. `qdrant` (private, persistent volume)

Canonical URLs and environment values are tracked in `docs/environments.md`.

## Design Principles

1. Retrieval transparency over framework complexity.
2. Citation-first answer output.
3. Main branch remains shippable.
4. Keep source modules small and composable.
