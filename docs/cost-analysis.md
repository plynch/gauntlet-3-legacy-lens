# LegacyLens Cost Analysis

## Assumptions

1. Query volume: `25 queries/user/day`.
2. Cost model buckets:
- embedding API usage
- LLM generation usage
- vector DB hosting/usage
3. Forecast values are planning estimates from presearch, not hard provider guarantees.

## User-Based Monthly Projections

1. `100 users`: about `$53/month` (`$0.53/user/month`)
2. `1,000 users`: about `$357/month` (`$0.36/user/month`)
3. `10,000 users`: about `$3,278/month` (`$0.33/user/month`)
4. `100,000 users`: about `$31,880/month` (`$0.32/user/month`)

## Interpretation

1. LLM generation is expected to be the largest variable cost.
2. Embeddings are lower per request but scale with ingestion/re-index frequency.
3. Qdrant cost is mainly infrastructure usage and growth of stored vectors.

## Cost Controls

1. Keep context windows bounded (`LEGACYLENS_MAX_CONTEXT_CHARACTERS`).
2. Prefer incremental ingest to avoid re-embedding unchanged files.
3. Tune `top_k` to avoid unnecessary context expansion.
4. Use deterministic fallback mode during non-critical development sessions.

## Notes for Final Submission

1. Re-check model prices near final submission date.
2. Record measured staging query/token behavior alongside this forecast.
3. Keep assumptions explicit in report text.
