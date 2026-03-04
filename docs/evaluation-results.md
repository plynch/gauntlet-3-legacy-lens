# Evaluation Results (MVP Evidence)

Captured on: 2026-03-03 (America/Chicago, CST)

## Environment Health Checks

| Environment | Endpoint | Result |
| --- | --- | --- |
| staging | `GET https://legacy-lens-api-staging.up.railway.app/api/health` | `{"status":"ok","service":"LegacyLens API (Staging)","qdrant_configured":true}` |
| production | `GET https://legacy-lens-api.up.railway.app/api/health` | `{"status":"ok","service":"LegacyLens API (Production)","qdrant_configured":true}` |

## Full-Corpus Ingest Evidence

Source corpus: [GnuCOBOL SourceForge trunk](https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/)

| Environment | Mode | Files Seen | Files Indexed | Files Not Indexable | Chunks Indexed | Corpus LOC | Duration |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| staging | full | 418 | 417 | 1 | 8929 | 571724 | 345.71s |
| production | full | 418 | 417 | 1 | 8929 | 571724 | 352.83s |

Not-indexable file reported by both environments:

- `data/corpus/sourceforge-trunk/config/runtime_empty.cfg (no indexable content)`

## Query API Evidence

Endpoint used: `POST /api/query`

Representative question:

- `Where is file I/O handled in GnuCOBOL?`

Observed behavior in both staging and production:

1. Non-empty grounded answer returned.
2. `insufficient_evidence` returned as `false`.
3. Citations array returned with file/line references.
4. Evidence snippets returned with scores and matching citations.

Representative citation paths returned:

- `data/corpus/sourceforge-trunk/libcob/fileio.c:1-80`
- `data/corpus/sourceforge-trunk/libcob/foci.c:1-80`
- `data/corpus/sourceforge-trunk/libcob/focextfh.c:1-80`

## Feature API Evidence (Optional Surface)

Endpoint checks on staging:

1. `GET /api/features` returns the 5 documented feature keys.
2. `POST /api/features/dependency_mapping/query` returns answer + citations + snippets.

This verifies feature APIs are available even though the default MVP UI is centered on free-form query.
