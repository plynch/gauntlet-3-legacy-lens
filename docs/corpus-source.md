# Corpus Source of Truth

LegacyLens ingests **only** the latest GnuCOBOL SourceForge trunk snapshot.

Canonical upstream link:

- [GnuCOBOL SourceForge trunk](https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/)

## Local sync workflow

1. Sync latest SourceForge trunk snapshot into the repo corpus directory:

```bash
./scripts/fetch-sourceforge-trunk.sh
```

2. Confirm corpus path contains files:

```bash
find backend/data/corpus/sourceforge-trunk -type f \( -name '*.cbl' -o -name '*.cob' -o -name '*.cpy' -o -name '*.copy' \) | wc -l
```

3. Run full ingest:

```bash
curl -X POST 'http://localhost:8000/api/ingest?mode=full'
```

Staging/prod one-call option:

```bash
curl -X POST 'https://<api-domain>/api/corpus/sourceforge/full-ingest'
```

## Runtime configuration

The backend must point to this directory only:

```env
LEGACYLENS_SOURCE_DIRECTORIES=["data/corpus/sourceforge-trunk"]
```
