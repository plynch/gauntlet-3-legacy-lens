export interface HealthResponse {
  status: string
  service: string
  timestamp: string
  qdrant_configured: boolean
}

export interface QueryRequest {
  question: string
  top_k?: number
}

export interface Citation {
  path: string
  line_start: number
  line_end: number
  section?: string | null
}

export interface RetrievedSnippet {
  text: string
  score: number
  citation: Citation
}

export interface QueryResponse {
  question: string
  answer: string
  insufficient_evidence: boolean
  snippets: RetrievedSnippet[]
  citations: Citation[]
}

export interface IngestStats {
  mode: 'full' | 'incremental'
  started_at: string
  completed_at: string
  duration_seconds: number
  files_seen: number
  files_indexed: number
  files_skipped: number
  files_unchanged?: number
  files_not_indexable?: number
  chunks_indexed: number
  corpus_bytes: number
  corpus_loc: number
  skipped_paths?: string[]
}

export interface IngestStatus {
  active: boolean
  phase: 'idle' | 'syncing' | 'indexing' | 'completed' | 'failed'
  mode: 'full' | 'incremental' | null
  started_at: string | null
  updated_at: string
  sync_started_at: string | null
  sync_completed_at: string | null
  sync_files_synced: number | null
  sync_corpus_loc: number | null
  sync_corpus_bytes: number | null
  ingest_stats: IngestStats | null
  last_indexed_at: string | null
  has_indexed_data: boolean
  summary: string | null
  error: string | null
  error_stage: 'sync' | 'indexing' | null
}

export interface SourceForgeSyncStats {
  source_url: string
  destination_path: string
  synced_at: string
  files_synced: number
  corpus_loc: number
  corpus_bytes: number
}

export interface SourceForgeFullIngestResponse {
  sync: SourceForgeSyncStats
  ingest: IngestStats
}

export interface FeatureDefinition {
  key: string
  title: string
  description: string
  requires_subject: boolean
  example_subject?: string | null
}

export interface FeatureListResponse {
  features: FeatureDefinition[]
}

const fallbackApiBase = 'http://localhost:8000'
const fallbackSourceRepoBase = 'https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk'

type RuntimeConfig = {
  API_BASE_URL?: string
  SOURCE_REPO_BASE_URL?: string
  ENABLE_INGEST_CONTROLS?: string | boolean
}

function getRuntimeConfig(): RuntimeConfig | undefined {
  const globalWindow = window as typeof window & { __APP_CONFIG__?: RuntimeConfig }
  return globalWindow.__APP_CONFIG__
}

function normalizeApiBase(rawValue: string | undefined): string {
  const value = (rawValue || '').trim()
  if (!value) return fallbackApiBase

  const withoutQuotes =
    (value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))
      ? value.slice(1, -1)
      : value

  return withoutQuotes.replace(/\/+$/, '')
}

function normalizeOptionalBase(rawValue: string | undefined): string {
  const value = (rawValue || '').trim()
  if (!value) return ''

  const withoutQuotes =
    (value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))
      ? value.slice(1, -1)
      : value

  return withoutQuotes.replace(/\/+$/, '')
}

function parseBooleanFlag(rawValue: string | boolean | undefined, defaultValue: boolean): boolean {
  if (typeof rawValue === 'boolean') {
    return rawValue
  }
  if (typeof rawValue !== 'string') {
    return defaultValue
  }

  const trimmed = rawValue.trim()
  const unquoted =
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
      ? trimmed.slice(1, -1)
      : trimmed
  const normalized = unquoted.trim().toLowerCase()
  if (!normalized) return defaultValue
  if (['0', 'false', 'off', 'no', 'disabled'].includes(normalized)) return false
  if (['1', 'true', 'on', 'yes', 'enabled'].includes(normalized)) return true
  return defaultValue
}

function getApiBase(): string {
  return normalizeApiBase(
    getRuntimeConfig()?.API_BASE_URL || (import.meta.env.VITE_API_BASE_URL as string | undefined),
  )
}

function getSourceRepoBase(): string {
  const configuredBase = normalizeOptionalBase(
    getRuntimeConfig()?.SOURCE_REPO_BASE_URL ||
      (import.meta.env.VITE_SOURCE_REPO_BASE_URL as string | undefined),
  )
  return configuredBase || fallbackSourceRepoBase
}

function normalizeSourcePath(path: string): string {
  const trimmed = path.trim().replace(/^\/+/, '')
  const knownPrefixes = [
    'backend/data/corpus/sourceforge-trunk/',
    'data/corpus/sourceforge-trunk/',
    'sourceforge-trunk/',
    'trunk/',
  ]

  for (const prefix of knownPrefixes) {
    if (trimmed.startsWith(prefix)) {
      return trimmed.slice(prefix.length)
    }
  }

  return trimmed
}

export function buildSourceLink(path: string, lineStart: number, lineEnd: number): string | null {
  const base = getSourceRepoBase()
  const repoPath = normalizeSourcePath(path)
  if (!repoPath) return base

  const normalizedPath = repoPath
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/")

  const start = Number.isFinite(lineStart) ? Math.max(1, Math.trunc(lineStart)) : 1
  void lineEnd
  // SourceForge reliably supports single-line anchors only.
  return `${base}/${normalizedPath}?r=HEAD#l${start}`
}

export function areIngestControlsEnabled(): boolean {
  const runtimeFlag = getRuntimeConfig()?.ENABLE_INGEST_CONTROLS
  const envFlag = import.meta.env.VITE_ENABLE_INGEST_CONTROLS as string | undefined
  return parseBooleanFlag(runtimeFlag ?? envFlag, true)
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${getApiBase()}/api/health`)

  if (!response.ok) {
    throw new Error(`Health endpoint returned ${response.status}`)
  }

  return response.json()
}

export async function runQuery(request: QueryRequest): Promise<QueryResponse> {
  const response = await fetch(`${getApiBase()}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    let detail = `Query endpoint returned ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) {
        detail = payload.detail
      }
    } catch {
      // Keep the default error string when body is not JSON.
    }
    throw new Error(detail)
  }

  return response.json()
}

export async function runIngest(mode: 'full' | 'incremental' = 'incremental'): Promise<IngestStats> {
  const response = await fetch(`${getApiBase()}/api/ingest?mode=${mode}`, { method: 'POST' })

  if (!response.ok) {
    let detail = `Ingest endpoint returned ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) {
        detail = payload.detail
      }
    } catch {
      // Keep default message if response body is not JSON.
    }
    throw new Error(detail)
  }

  return response.json()
}

export async function getIngestRuns(limit = 5): Promise<IngestStats[]> {
  const safeLimit = Math.max(1, Math.min(limit, 200))
  const response = await fetch(`${getApiBase()}/api/ingest/runs?limit=${safeLimit}`)

  if (!response.ok) {
    let detail = `Ingest history endpoint returned ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) {
        detail = payload.detail
      }
    } catch {
      // Keep default message if response body is not JSON.
    }
    throw new Error(detail)
  }

  return response.json()
}

export async function getIngestStatus(): Promise<IngestStatus> {
  const response = await fetch(`${getApiBase()}/api/ingest/status`)

  if (!response.ok) {
    let detail = `Ingest status endpoint returned ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) {
        detail = payload.detail
      }
    } catch {
      // Keep default message if response body is not JSON.
    }
    throw new Error(detail)
  }

  return response.json()
}

export async function runSourceForgeFullIngest(): Promise<SourceForgeFullIngestResponse> {
  const response = await fetch(`${getApiBase()}/api/corpus/sourceforge/full-ingest`, { method: 'POST' })

  if (!response.ok) {
    let detail = `SourceForge full ingest endpoint returned ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) {
        detail = payload.detail
      }
    } catch {
      // Keep default message if response body is not JSON.
    }
    throw new Error(detail)
  }

  return response.json()
}

export async function syncSourceForge(): Promise<SourceForgeSyncStats> {
  const response = await fetch(`${getApiBase()}/api/corpus/sourceforge/sync`, { method: 'POST' })

  if (!response.ok) {
    let detail = `SourceForge sync endpoint returned ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) {
        detail = payload.detail
      }
    } catch {
      // Keep default message if response body is not JSON.
    }
    throw new Error(detail)
  }

  return response.json()
}

export async function getFeatures(): Promise<FeatureDefinition[]> {
  const response = await fetch(`${getApiBase()}/api/features`)

  if (!response.ok) {
    throw new Error(`Features endpoint returned ${response.status}`)
  }

  const payload = (await response.json()) as FeatureListResponse
  return payload.features
}

export async function runFeatureQuery(
  featureKey: string,
  subject?: string,
  topK?: number,
): Promise<QueryResponse> {
  const response = await fetch(`${getApiBase()}/api/features/${featureKey}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject, top_k: topK }),
  })

  if (!response.ok) {
    let detail = `Feature query endpoint returned ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) {
        detail = payload.detail
      }
    } catch {
      // Keep default message if response body is not JSON.
    }
    throw new Error(detail)
  }

  return response.json()
}
