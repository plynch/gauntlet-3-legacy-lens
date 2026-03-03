# Environment Endpoints

Canonical Railway environments and URLs for LegacyLens.

## Staging

1. Frontend: `https://legacy-lens-staging.up.railway.app/`
2. API: `https://legacy-lens-api-staging.up.railway.app/`
3. Branch mapping: `main` -> `staging`

Required key vars:

```env
# API service
LEGACYLENS_ALLOWED_ORIGINS=["https://legacy-lens-staging.up.railway.app"]
LEGACYLENS_SOURCE_DIRECTORIES=["data/corpus/sourceforge-trunk"]

# Frontend service
VITE_API_BASE_URL=https://legacy-lens-api-staging.up.railway.app
VITE_SOURCE_REPO_BASE_URL=https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk
```

## Production

1. Frontend: `https://legacy-lens.up.railway.app/`
2. API: `https://legacy-lens-api.up.railway.app/`
3. Branch mapping: `production` -> `production`

Required key vars:

```env
# API service
LEGACYLENS_ALLOWED_ORIGINS=["https://legacy-lens.up.railway.app"]
LEGACYLENS_SOURCE_DIRECTORIES=["data/corpus/sourceforge-trunk"]

# Frontend service
VITE_API_BASE_URL=https://legacy-lens-api.up.railway.app
VITE_SOURCE_REPO_BASE_URL=https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk
```

## Update Rule

1. Update this file first when a Railway domain changes.
2. Mirror the same values into local `.env.staging` or `.env.production`.
3. Paste the matching values into Railway service variables.

## Corpus Source of Truth

1. GnuCOBOL trunk source link:
- `https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/`
2. LegacyLens ingests only this trunk snapshot synced into `data/corpus/sourceforge-trunk`.
