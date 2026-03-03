export interface HealthResponse {
  status: string
  service: string
  timestamp: string
  qdrant_configured: boolean
}

const fallbackApiBase = 'http://localhost:8000'

type RuntimeConfig = {
  API_BASE_URL?: string
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

export async function getHealth(): Promise<HealthResponse> {
  const apiBase = normalizeApiBase(
    getRuntimeConfig()?.API_BASE_URL || (import.meta.env.VITE_API_BASE_URL as string | undefined),
  )
  const response = await fetch(`${apiBase}/api/health`)

  if (!response.ok) {
    throw new Error(`Health endpoint returned ${response.status}`)
  }

  return response.json()
}
