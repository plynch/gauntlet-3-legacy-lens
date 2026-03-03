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
  files_seen: number
  files_indexed: number
  files_skipped: number
  chunks_indexed: number
}

const fallbackApiBase = 'http://localhost:8000'

type RuntimeConfig = {
  API_BASE_URL?: string
  SOURCE_REPO_BASE_URL?: string
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

function getApiBase(): string {
  return normalizeApiBase(
    getRuntimeConfig()?.API_BASE_URL || (import.meta.env.VITE_API_BASE_URL as string | undefined),
  )
}

function getSourceRepoBase(): string {
  return normalizeOptionalBase(
    getRuntimeConfig()?.SOURCE_REPO_BASE_URL ||
      (import.meta.env.VITE_SOURCE_REPO_BASE_URL as string | undefined),
  )
}

export function buildSourceLink(path: string, lineStart: number, lineEnd: number): string | null {
  const base = getSourceRepoBase()
  if (!base) {
    return null
  }

  const normalizedPath = path
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/")

  return `${base}/${normalizedPath}#L${lineStart}-L${lineEnd}`
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
