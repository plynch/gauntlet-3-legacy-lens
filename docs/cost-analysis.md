# LegacyLens Cost Analysis

As of **Wednesday, March 4, 2026 (about 12:30 PM CT)**.

## Actual Development Spend (Observed)

### OpenAI usage (observed)

1. Embedding tokens: about `74.8M` total input tokens in period.
2. High-volume ingest day: about `50.1M` embedding tokens on March 3.
3. User-reported embedding cost for high-volume day: about `$1.00`.
4. OpenAI dashboard total spend shown: about `$1.81`.

### Railway usage (observed for `legacy-lens`)

1. Current project cost shown: about `$0.846`.
2. Estimated monthly shown: about `$10.87` to `$10.88`.
3. Cost breakdown shown:
- Memory: `$0.7978`
- CPU: `$0.0131`
- Egress: `$0.0148`
- Volume: `$0.0206`

### Combined observed dev spend so far (approximate)

1. OpenAI (`$1.81`) + Railway (`$0.846`) = about `$2.66`.

## Production Projection Baseline

Near-term baseline projection from current Railway estimate:

1. Infrastructure-only baseline: about `$10.87/month` (can vary with uptime/resources).
2. This does **not** include growth in OpenAI query/inference spend at larger user volume.

## User-Based Monthly Projections (Planning Model)

Assumption: `25 queries/user/day`.

1. `100 users`: about `$53/month` (`$0.53/user/month`)
2. `1,000 users`: about `$357/month` (`$0.36/user/month`)
3. `10,000 users`: about `$3,278/month` (`$0.33/user/month`)
4. `100,000 users`: about `$31,880/month` (`$0.32/user/month`)

## Cost Drivers (Current vs Scale)

1. Current observed dominant driver is **memory** (not volume yet).
2. At scale, major drivers are expected to be:
- LLM generation usage
- embedding volume for re-indexes/new code
- sustained RAM/CPU usage
- volume growth over time

## Cost Controls Implemented

1. Full ingest now clears stale vectors first to avoid duplicate legacy corpus buildup.
2. Incremental ingest skips unchanged files by hash.
3. Context budget is bounded (`LEGACYLENS_MAX_CONTEXT_CHARACTERS`).
4. Retrieval depth is bounded (`LEGACYLENS_QUERY_TOP_K`).

## Cost Controls Recommended Next

1. Disable user-facing ingest controls in production (`VITE_ENABLE_INGEST_CONTROLS=false`).
2. Run scheduled ingest via Railway Cron jobs instead of ad-hoc manual triggers.
3. Use incremental ingest on a daily cadence; reserve full ingest for less frequent maintenance windows.
4. Keep volume backups/snapshots intentional to limit storage growth.

## Notes

1. Railway resource prices and feature behavior are documented at:
- https://docs.railway.com/pricing
- https://docs.railway.com/reference/cron-jobs
2. All costs above are snapshots and should be refreshed at final submission time.
