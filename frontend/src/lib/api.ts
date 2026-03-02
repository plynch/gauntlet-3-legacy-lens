export interface HealthResponse {
  status: string
  service: string
  timestamp: string
  qdrant_configured: boolean
}

const fallbackApiBase = 'http://localhost:8000'

const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined) || fallbackApiBase

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiBase}/api/health`)

  if (!response.ok) {
    throw new Error(`Health endpoint returned ${response.status}`)
  }

  return response.json()
}
