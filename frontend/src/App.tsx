import { FormEvent, useEffect, useState } from 'react'
import {
  HealthResponse,
  IngestStats,
  QueryResponse,
  buildSourceLink,
  getHealth,
  runIngest,
  runQuery,
} from './lib/api'

type IngestMode = 'full' | 'incremental'

function formatIngestSummary(stats: IngestStats, mode: IngestMode | null): string {
  if (stats.files_seen === 0) {
    return 'No source files were discovered in configured source directories.'
  }

  if (stats.files_indexed === 0 && stats.files_skipped === stats.files_seen) {
    if (mode === 'incremental') {
      return `No changed files detected. ${stats.files_skipped}/${stats.files_seen} files were skipped as unchanged.`
    }

    return `No chunks were indexed. ${stats.files_skipped}/${stats.files_seen} files were skipped (likely empty or unchunkable).`
  }

  return `Indexed ${stats.files_indexed}/${stats.files_seen} files and ${stats.chunks_indexed} chunks (${stats.files_skipped} skipped).`
}

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthLoading, setHealthLoading] = useState(false)
  const [healthError, setHealthError] = useState<string>('')
  const [query, setQuery] = useState('')
  const [queryLoading, setQueryLoading] = useState(false)
  const [queryError, setQueryError] = useState<string>('')
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null)
  const [ingestLoadingMode, setIngestLoadingMode] = useState<IngestMode | null>(null)
  const [ingestError, setIngestError] = useState<string>('')
  const [ingestStats, setIngestStats] = useState<IngestStats | null>(null)
  const [lastIngestMode, setLastIngestMode] = useState<IngestMode | null>(null)

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

  async function onIngestClick(mode: IngestMode) {
    setIngestLoadingMode(mode)
    setLastIngestMode(mode)
    setIngestError('')
    setIngestStats(null)

    try {
      const stats = await runIngest(mode)
      setIngestStats(stats)
    } catch (err: unknown) {
      setIngestError(err instanceof Error ? err.message : 'Ingestion failed')
    } finally {
      setIngestLoadingMode(null)
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
          <ul className="health-list">
            <li>Status: {health.status}</li>
            <li>Service: {health.service}</li>
            <li>Qdrant configured: {health.qdrant_configured ? 'yes' : 'no'}</li>
            <li>Timestamp: {new Date(health.timestamp).toLocaleString()}</li>
          </ul>
        ) : null}
        <div className="button-row">
          <button onClick={loadHealth} disabled={healthLoading}>
            {healthLoading ? 'Refreshing...' : 'Refresh health'}
          </button>
        </div>
        <div className="button-row">
          <button onClick={() => onIngestClick('incremental')} disabled={ingestLoadingMode !== null}>
            {ingestLoadingMode === 'incremental' ? 'Indexing changes...' : 'Index changes'}
          </button>
          <button
            className="secondary-button"
            onClick={() => onIngestClick('full')}
            disabled={ingestLoadingMode !== null}
          >
            {ingestLoadingMode === 'full' ? 'Reindexing...' : 'Reindex all'}
          </button>
        </div>
        <p className="muted-note">
          Use <strong>Index changes</strong> for normal use. Use <strong>Reindex all</strong> after chunking/model
          changes.
        </p>
        <div>
          {ingestError ? <p role="alert">Indexing issue: {ingestError}</p> : null}
          {ingestStats ? <p>{formatIngestSummary(ingestStats, lastIngestMode)}</p> : null}
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
          <pre className="answer-text">{queryResult.answer}</pre>
          {queryResult.insufficient_evidence ? <p>Evidence confidence: low</p> : null}

          {queryResult.citations.length > 0 ? (
            <>
              <h3>Citations</h3>
              <ul>
                {queryResult.citations.map((citation, index) => {
                  const sourceLink = buildSourceLink(citation.path, citation.line_start, citation.line_end)
                  return (
                    <li key={`${citation.path}-${citation.line_start}-${citation.line_end}`}>
                      [{index + 1}] {citation.path}:{citation.line_start}-{citation.line_end}
                      {citation.section ? ` (${citation.section})` : ''}
                      {sourceLink ? (
                        <>
                          {' '}
                          <a href={sourceLink} target="_blank" rel="noreferrer">
                            open source
                          </a>
                        </>
                      ) : null}
                    </li>
                  )
                })}
              </ul>
            </>
          ) : null}

          {queryResult.snippets.length > 0 ? (
            <>
              <h3>Evidence Snippets</h3>
              {queryResult.snippets.map((snippet) => {
                const sourceLink = buildSourceLink(
                  snippet.citation.path,
                  snippet.citation.line_start,
                  snippet.citation.line_end,
                )
                return (
                  <article
                    key={`${snippet.citation.path}-${snippet.citation.line_start}-${snippet.citation.line_end}`}
                  >
                    <p>
                      <strong>
                        {snippet.citation.path}:{snippet.citation.line_start}-{snippet.citation.line_end}
                      </strong>{' '}
                      score {snippet.score.toFixed(3)}
                      {sourceLink ? (
                        <>
                          {' '}
                          <a href={sourceLink} target="_blank" rel="noreferrer">
                            open source
                          </a>
                        </>
                      ) : null}
                    </p>
                    <pre>{snippet.text}</pre>
                  </article>
                )
              })}
            </>
          ) : null}
        </section>
      ) : null}
    </main>
  )
}

export default App
