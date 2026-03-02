import { FormEvent, useEffect, useState } from 'react'
import { HealthResponse, getHealth } from './lib/api'

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [query, setQuery] = useState('')

  async function loadHealth() {
    setLoading(true)
    setError('')

    try {
      const data = await getHealth()
      setHealth(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Health check failed')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadHealth()
  }, [])

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    window.alert(`Query placeholder: ${query || 'no query entered'}`)
  }

  return (
    <main className="shell">
      <h1>LegacyLens</h1>
      <p>Browser-ready skeleton for the legacy codebase RAG project.</p>

      <section>
        <h2>Service Status</h2>
        {loading ? (
          <p>Checking backend health…</p>
        ) : error ? (
          <p role="alert">Backend issue: {error}</p>
        ) : health ? (
          <ul>
            <li>Status: {health.status}</li>
            <li>Service: {health.service}</li>
            <li>Qdrant configured: {health.qdrant_configured ? 'yes' : 'no'}</li>
            <li>Timestamp: {new Date(health.timestamp).toLocaleString()}</li>
          </ul>
        ) : null}
        <button onClick={loadHealth}>Refresh health</button>
      </section>

      <section>
        <h2>Query</h2>
        <form onSubmit={onSubmit}>
          <label htmlFor="query">Ask about the codebase</label>
          <textarea
            id="query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            rows={4}
            placeholder="e.g., Where is file IO handled?"
          />
          <button type="submit">Submit (placeholder)</button>
        </form>
      </section>
    </main>
  )
}

export default App
