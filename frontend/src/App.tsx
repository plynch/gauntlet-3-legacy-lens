import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from 'react'
import {
  HealthResponse,
  QueryResponse,
  buildSourceLink,
  getHealth,
  runQuery,
} from './lib/api'
import { ServiceStatusPanel } from './components/ServiceStatusPanel'

const INLINE_CITATION_PATTERN = /\[([A-Za-z0-9_./-]+):(\d+)-(\d+)\]/g

function renderAnswerWithLinks(answer: string) {
  const matches = Array.from(answer.matchAll(INLINE_CITATION_PATTERN))
  if (matches.length === 0) {
    return answer
  }

  const nodes: Array<string | JSX.Element> = []
  let cursor = 0

  for (let index = 0; index < matches.length; index += 1) {
    const match = matches[index]
    const full = match[0]
    const path = match[1]
    const lineStart = Number.parseInt(match[2], 10)
    const lineEnd = Number.parseInt(match[3], 10)
    const matchIndex = match.index ?? 0

    if (matchIndex > cursor) {
      nodes.push(answer.slice(cursor, matchIndex))
    }

    const link = buildSourceLink(path, lineStart, lineEnd)
    if (link) {
      nodes.push(
        <a
          key={`answer-citation-${index}-${path}-${lineStart}-${lineEnd}`}
          href={link}
          target="_blank"
          rel="noreferrer"
          className="answer-inline-link"
        >
          {full}
        </a>,
      )
    } else {
      nodes.push(full)
    }

    cursor = matchIndex + full.length
  }

  if (cursor < answer.length) {
    nodes.push(answer.slice(cursor))
  }

  return nodes
}

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthLoading, setHealthLoading] = useState(false)
  const [healthError, setHealthError] = useState<string>('')
  const [query, setQuery] = useState('')
  const [queryLoading, setQueryLoading] = useState(false)
  const [queryError, setQueryError] = useState<string>('')
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null)
  const [queryHintVisible, setQueryHintVisible] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const queryHintTimeoutRef = useRef<number | null>(null)

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

  useEffect(() => {
    return () => {
      if (queryHintTimeoutRef.current !== null) {
        window.clearTimeout(queryHintTimeoutRef.current)
      }
    }
  }, [])

  function showQueryShortcutHint() {
    setQueryHintVisible(true)
    if (queryHintTimeoutRef.current !== null) {
      window.clearTimeout(queryHintTimeoutRef.current)
    }
    queryHintTimeoutRef.current = window.setTimeout(() => {
      setQueryHintVisible(false)
      queryHintTimeoutRef.current = null
    }, 2800)
  }

  async function submitQuery() {
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

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await submitQuery()
  }

  async function onQueryKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== 'Enter' || event.shiftKey) {
      return
    }
    event.preventDefault()
    await submitQuery()
  }

  return (
    <main className="shell app-shell">
      <header className="app-header">
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
      </header>

      <div className="workspace">
        <div className="query-column">
          <section className="query-panel">
            <h2>Query</h2>
            <form onSubmit={onSubmit}>
              <label htmlFor="query">Ask about the codebase</label>
              <textarea
                id="query"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onFocus={showQueryShortcutHint}
                onKeyDown={onQueryKeyDown}
                rows={4}
                placeholder="e.g., Where is file IO handled?"
              />
              {queryHintVisible ? <p className="query-shortcut-hint">Enter submits · Shift+Enter adds a newline</p> : null}
              <button type="submit" disabled={queryLoading}>
                {queryLoading ? 'Submitting...' : 'Submit'}
              </button>
            </form>
            {queryError ? <p role="alert">Query issue: {queryError}</p> : null}
          </section>

          {queryResult ? (
            <section>
              <h2>Answer</h2>
              <pre className="answer-text">{renderAnswerWithLinks(queryResult.answer)}</pre>
              {queryResult.insufficient_evidence ? <p>Evidence confidence: low</p> : null}

              {queryResult.citations.length > 0 ? (
                <>
                  <h3>Citations</h3>
                  <ul>
                    {queryResult.citations.map((citation, index) => {
                      const sourceLink = buildSourceLink(citation.path, citation.line_start, citation.line_end)
                      const label = `[${index + 1}] ${citation.path}:${citation.line_start}-${citation.line_end}`
                      return (
                        <li key={`${citation.path}-${citation.line_start}-${citation.line_end}`}>
                          {sourceLink ? (
                            <a href={sourceLink} target="_blank" rel="noreferrer">
                              {label}
                            </a>
                          ) : (
                            label
                          )}
                          {citation.section ? ` (${citation.section})` : ''}
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
                            {sourceLink ? (
                              <a href={sourceLink} target="_blank" rel="noreferrer">
                                {snippet.citation.path}:{snippet.citation.line_start}-{snippet.citation.line_end}
                              </a>
                            ) : (
                              `${snippet.citation.path}:${snippet.citation.line_start}-${snippet.citation.line_end}`
                            )}
                          </strong>{' '}
                          score {snippet.score.toFixed(3)}
                        </p>
                        <pre>{snippet.text}</pre>
                      </article>
                    )
                  })}
                </>
              ) : null}
            </section>
          ) : null}
        </div>

        <aside className={`status-sidebar${sidebarCollapsed ? ' collapsed' : ''}`} aria-label="Service status sidebar">
          <button
            className="secondary-button sidebar-toggle"
            onClick={() => setSidebarCollapsed((value) => !value)}
            aria-expanded={!sidebarCollapsed}
          >
            {sidebarCollapsed ? 'Show status + ingest' : 'Hide status + ingest'}
          </button>
          {!sidebarCollapsed ? (
            <ServiceStatusPanel
              health={health}
              healthLoading={healthLoading}
              healthError={healthError}
              onRefreshHealth={loadHealth}
            />
          ) : null}
        </aside>
      </div>
    </main>
  )
}

export default App
