import { FormEvent, useEffect, useState } from 'react'
import { HealthResponse, IngestStats, QueryResponse, getHealth, runIngest, runQuery } from './lib/api'

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthLoading, setHealthLoading] = useState(false)
  const [healthError, setHealthError] = useState<string>('')
  const [query, setQuery] = useState('')
  const [queryLoading, setQueryLoading] = useState(false)
  const [queryError, setQueryError] = useState<string>('')
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null)
  const [ingestLoading, setIngestLoading] = useState(false)
  const [ingestError, setIngestError] = useState<string>('')
  const [ingestStats, setIngestStats] = useState<IngestStats | null>(null)

  async function loadHealth() {
    setHealthLoading(true)
    setHealthError('')

    try {
      const data = await getHealth()
      setHealth(data)
    } catch (err: unknown) {
      setHealthError(err instanceof Error ? err.message : 'Health check failed')
    } finally {
      setHealthLoading(false)
    }
  }

  useEffect(() => {
    loadHealth()
  }, [])

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedQuery = query.trim()
    if (!trimmedQuery) {
      setQueryError('Please enter a question.')
      setQueryResult(null)
      return
    }

    setQueryLoading(true)
    setQueryError('')
    setQueryResult(null)

    try {
      const result = await runQuery({ question: trimmedQuery })
      setQueryResult(result)
    } catch (err: unknown) {
      setQueryError(err instanceof Error ? err.message : 'Query failed')
    } finally {
      setQueryLoading(false)
    }
  }

  async function onIngestClick() {
    setIngestLoading(true)
    setIngestError('')
    try {
      const stats = await runIngest('incremental')
      setIngestStats(stats)
    } catch (err: unknown) {
      setIngestError(err instanceof Error ? err.message : 'Ingestion failed')
    } finally {
      setIngestLoading(false)
    }
  }

  return (
    <main className="shell">
      <h1>LegacyLens</h1>
      <p>Browser-ready skeleton for the legacy codebase RAG project.</p>

      <section>
        <h2>Service Status</h2>
        {healthLoading ? (
          <p>Checking backend health…</p>
        ) : healthError ? (
          <p role="alert">Backend issue: {healthError}</p>
        ) : health ? (
          <ul>
            <li>Status: {health.status}</li>
            <li>Service: {health.service}</li>
            <li>Qdrant configured: {health.qdrant_configured ? 'yes' : 'no'}</li>
            <li>Timestamp: {new Date(health.timestamp).toLocaleString()}</li>
          </ul>
        ) : null}
        <button onClick={loadHealth}>Refresh health</button>
        <div>
          <button onClick={onIngestClick} disabled={ingestLoading}>
            {ingestLoading ? 'Indexing...' : 'Index corpus'}
          </button>
          {ingestError ? <p role="alert">Indexing issue: {ingestError}</p> : null}
          {ingestStats ? (
            <p>
              Indexed {ingestStats.files_indexed}/{ingestStats.files_seen} files, {ingestStats.chunks_indexed}{' '}
              chunks ({ingestStats.files_skipped} skipped).
            </p>
          ) : null}
        </div>
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
          <button type="submit" disabled={queryLoading}>
            {queryLoading ? 'Submitting...' : 'Submit'}
          </button>
        </form>
        {queryError ? <p role="alert">Query issue: {queryError}</p> : null}
      </section>

      {queryResult ? (
        <section>
          <h2>Answer</h2>
          <p>{queryResult.answer}</p>
          {queryResult.insufficient_evidence ? <p>Evidence confidence: low</p> : null}

          {queryResult.citations.length > 0 ? (
            <>
              <h3>Citations</h3>
              <ul>
                {queryResult.citations.map((citation) => (
                  <li key={`${citation.path}-${citation.line_start}-${citation.line_end}`}>
                    {citation.path}:{citation.line_start}-{citation.line_end}
                    {citation.section ? ` (${citation.section})` : ''}
                  </li>
                ))}
              </ul>
            </>
          ) : null}

          {queryResult.snippets.length > 0 ? (
            <>
              <h3>Evidence Snippets</h3>
              {queryResult.snippets.map((snippet) => (
                <article key={`${snippet.citation.path}-${snippet.citation.line_start}-${snippet.citation.line_end}`}>
                  <p>
                    <strong>
                      {snippet.citation.path}:{snippet.citation.line_start}-{snippet.citation.line_end}
                    </strong>{' '}
                    score {snippet.score.toFixed(3)}
                  </p>
                  <pre>{snippet.text}</pre>
                </article>
              ))}
            </>
          ) : null}
        </section>
      ) : null}
    </main>
  )
}

export default App
