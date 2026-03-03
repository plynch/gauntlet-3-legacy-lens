# Ingest Benchmarks

This log records ingest benchmark runs with exact timing and corpus size metrics.

## Corpus source policy

- Canonical source of truth: [GnuCOBOL SourceForge trunk](https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/)
- Ingest directory: `data/corpus/sourceforge-trunk`
- Sync command: `./scripts/fetch-sourceforge-trunk.sh`

## Historical baseline dataset used for initial benchmark wiring

- Label: `GnuCOBOL Git mirror snapshot (pre-SourceForge switch)`
- Source snapshot path (local run): `/tmp/legacylens-bench/gnucobol-src`
- COBOL files discovered (`.cbl/.cob/.cpy/.copy`): `9`
- Corpus LOC at baseline: `1746`
- Corpus bytes at baseline: `69637`

## Run log

| Run started (UTC) | Run ended (UTC) | Mode | Files seen | Files indexed | Files skipped | Chunks indexed | Corpus LOC | Corpus bytes | Duration (s) | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-03-03T14:42:27.140652Z | 2026-03-03T14:42:27.287607Z | full | 9 | 9 | 0 | 28 | 1746 | 69637 | 0.146955 | Baseline full ingest over downloaded GnuCOBOL corpus snapshot. |
| 2026-03-03T14:43:05.328030Z | 2026-03-03T14:43:05.705830Z | incremental | 9 | 0 | 9 | 0 | 1746 | 69637 | 0.377800 | No file changes between runs (expected all skipped). |
| 2026-03-03T14:43:58.893385Z | 2026-03-03T14:43:59.274342Z | incremental | 9 | 1 | 8 | 7 | 1747 | 69677 | 0.380957 | One file touched (`numeric-dump.cob`) before run. |

## Notes

- Ingest telemetry is now returned by `POST /api/ingest` and stored in `backend/data/benchmarks/ingest_runs.jsonl`.
- For large-corpus target testing (for example 10,000 LOC under 5 minutes), point `LEGACYLENS_SOURCE_DIRECTORIES` at the larger corpus and repeat the same benchmark sequence.
