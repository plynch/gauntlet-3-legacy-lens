import { FormEvent, useEffect, useState } from 'react'
import {
  HealthResponse,
  QueryResponse,
  buildSourceLink,
  getHealth,
  runQuery,
} from './lib/api'
import { ServiceStatusPanel } from './components/ServiceStatusPanel'

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthLoading, setHealthLoading] = useState(false)
  const [healthError, setHealthError] = useState<string>('')
  const [query, setQuery] = useState('')
  const [queryLoading, setQueryLoading] = useState(false)
  const [queryError, setQueryError] = useState<string>('')
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null)

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

  return (
    <main className="shell">
      <h1>LegacyLens</h1>
      <p>
        LegacyLens is a retrieval-augmented analysis tool for the GnuCOBOL codebase, designed to answer architecture
        and behavior questions with grounded code citations from the upstream source tree.
      </p>
      <p className="muted-note">
        Source corpus:{' '}
        <a href="https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/" target="_blank" rel="noreferrer">
          GnuCOBOL SourceForge trunk
        </a>
      </p>

      <ServiceStatusPanel
        health={health}
        healthLoading={healthLoading}
        healthError={healthError}
        onRefreshHealth={loadHealth}
      />

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
