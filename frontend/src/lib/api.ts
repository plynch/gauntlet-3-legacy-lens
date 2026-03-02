export interface HealthResponse {
  status: string
  service: string
  timestamp: string
  qdrant_configured: boolean
}

const fallbackApiBase = 'http://localhost:8000'

function normalizeApiBase(rawValue: string | undefined): string {
  const value = (rawValue || '').trim()
  if (!value) return fallbackApiBase

  const withoutQuotes =
    (value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))
      ? value.slice(1, -1)
      : value

  return withoutQuotes.replace(/\/+$/, '')
}

const apiBase = normalizeApiBase(import.meta.env.VITE_API_BASE_URL as string | undefined)

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiBase}/api/health`)

  if (!response.ok) {
    throw new Error(`Health endpoint returned ${response.status}`)
  }

  return response.json()
}
