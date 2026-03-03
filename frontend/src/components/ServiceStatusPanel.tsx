import { useEffect, useMemo, useState } from 'react'
import { HealthResponse, IngestStats, getIngestRuns, runIngest, syncSourceForge } from '../lib/api'

type IngestMode = 'full' | 'incremental'
type PipelinePhase = 'idle' | 'syncing' | 'indexing' | 'completed' | 'failed'

type ServiceStatusPanelProps = {
  health: HealthResponse | null
  healthLoading: boolean
  healthError: string
  onRefreshHealth: () => Promise<void> | void
}

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

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(2)}s`
  }
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds - minutes * 60
  return `${minutes}m ${remainder.toFixed(2)}s`
}

function formatSecondsPerTenThousandLoc(durationSeconds: number, corpusLoc: number): string {
  if (corpusLoc <= 0) {
    return 'n/a'
  }
  const secondsPerTenThousand = (durationSeconds * 10000) / corpusLoc
  return formatDuration(secondsPerTenThousand)
}

function phaseLabel(phase: PipelinePhase): string {
  switch (phase) {
    case 'syncing':
      return 'Syncing SourceForge trunk'
    case 'indexing':
      return 'Indexing source files'
    case 'completed':
      return 'Ingest completed'
    case 'failed':
      return 'Ingest failed'
    default:
      return 'Idle'
  }
}

function progressPercent(phase: PipelinePhase, elapsedSeconds: number): number {
  if (phase === 'idle') return 0
  if (phase === 'syncing') return Math.min(35, 8 + elapsedSeconds * 2)
  if (phase === 'indexing') return Math.min(95, 35 + elapsedSeconds * 0.45)
  if (phase === 'completed') return 100
  return 100
}

export function ServiceStatusPanel(props: ServiceStatusPanelProps) {
  const { health, healthError, healthLoading, onRefreshHealth } = props
  const [ingestLoadingMode, setIngestLoadingMode] = useState<IngestMode | null>(null)
  const [ingestError, setIngestError] = useState<string>('')
  const [ingestStats, setIngestStats] = useState<IngestStats | null>(null)
  const [lastIngestMode, setLastIngestMode] = useState<IngestMode | null>(null)
  const [syncSummary, setSyncSummary] = useState<string>('')
  const [pipelinePhase, setPipelinePhase] = useState<PipelinePhase>('idle')
  const [operationStartedAt, setOperationStartedAt] = useState<number | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [lastIndexedAt, setLastIndexedAt] = useState<string | null>(null)

  useEffect(() => {
    if (!operationStartedAt || (pipelinePhase !== 'syncing' && pipelinePhase !== 'indexing')) {
      return undefined
    }
    const interval = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - operationStartedAt) / 1000))
    }, 1000)
    return () => window.clearInterval(interval)
  }, [operationStartedAt, pipelinePhase])

  useEffect(() => {
    let cancelled = false

    async function loadLastIngestRun() {
      try {
        const runs = await getIngestRuns(1)
        if (cancelled || runs.length === 0) return
        setLastIndexedAt(runs[0].completed_at)
      } catch {
        // keep label quiet if history endpoint is unavailable
      }
    }

    loadLastIngestRun()
    return () => {
      cancelled = true
    }
  }, [])

  const skipWarning = useMemo(() => {
    if (!ingestStats || ingestStats.files_skipped === 0) return null
    if (ingestStats.mode === 'incremental' && ingestStats.files_indexed === 0) return null
    return `Skipped ${ingestStats.files_skipped} file(s). Reindex all is recommended to retry skipped files after configuration updates.`
  }, [ingestStats])

  async function onIngestClick(mode: IngestMode) {
    setIngestLoadingMode(mode)
    setLastIngestMode(mode)
    setIngestError('')
    setIngestStats(null)
    setSyncSummary('')
    setPipelinePhase('indexing')
    setOperationStartedAt(Date.now())
    setElapsedSeconds(0)

    try {
      const stats = await runIngest(mode)
      setIngestStats(stats)
      setLastIndexedAt(stats.completed_at)
      setPipelinePhase('completed')
    } catch (err: unknown) {
      setPipelinePhase('failed')
      setIngestError(err instanceof Error ? err.message : 'Ingestion failed')
    } finally {
      setIngestLoadingMode(null)
    }
  }

  async function onSourceForgeFullIngestClick() {
    setIngestLoadingMode('full')
    setLastIngestMode('full')
    setIngestError('')
    setIngestStats(null)
    setSyncSummary(`Began syncing SourceForge trunk at ${new Date().toLocaleString()}.`)
    setPipelinePhase('syncing')
    setOperationStartedAt(Date.now())
    setElapsedSeconds(0)

    try {
      const syncStats = await syncSourceForge()
      setSyncSummary(
        `Finished SourceForge sync (${syncStats.files_synced} files, ${syncStats.corpus_loc} LOC) at ${new Date(
          syncStats.synced_at,
        ).toLocaleString()}.`,
      )

      setPipelinePhase('indexing')
      const stats = await runIngest('full')
      setIngestStats(stats)
      setLastIndexedAt(stats.completed_at)
      setPipelinePhase('completed')
    } catch (err: unknown) {
      setPipelinePhase('failed')
      setIngestError(err instanceof Error ? err.message : 'SourceForge sync + reindex failed')
    } finally {
      setIngestLoadingMode(null)
    }
  }

  const progress = progressPercent(pipelinePhase, elapsedSeconds)
  const isBusy = ingestLoadingMode !== null
  const isSyncing = pipelinePhase === 'syncing'
  const isIndexing = pipelinePhase === 'indexing'

  return (
    <section>
      <h2>Service Status</h2>
      {healthLoading ? (
        <p>Checking backend health...</p>
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

      <div className="ingest-actions">
        <button className="primary-action" onClick={onSourceForgeFullIngestClick} disabled={isBusy}>
          {isSyncing || (isIndexing && lastIngestMode === 'full')
            ? 'Syncing + reindexing...'
            : 'Sync SourceForge + Reindex'}
        </button>
        <button onClick={() => onIngestClick('incremental')} disabled={isBusy}>
          {isIndexing && lastIngestMode === 'incremental' ? 'Indexing changes...' : 'Index changes'}
        </button>
        <div className="action-stack">
          <button className="secondary-button" onClick={() => onIngestClick('full')} disabled={isBusy}>
            {isIndexing && lastIngestMode === 'full' ? 'Reindexing...' : 'Reindex all'}
          </button>
          <p className="last-indexed-note">
            Last indexed at: {lastIndexedAt ? new Date(lastIndexedAt).toLocaleString() : 'not yet indexed'}
          </p>
        </div>
        <button className="secondary-button" onClick={onRefreshHealth} disabled={healthLoading || isBusy}>
          {healthLoading ? 'Refreshing...' : 'Refresh health'}
        </button>
      </div>

      <p className="muted-note">
        Recommended flow: <strong>Sync SourceForge + Reindex</strong> first, then use <strong>Index changes</strong>{' '}
        for routine updates.
      </p>

      {pipelinePhase !== 'idle' ? (
        <div className="progress-panel" aria-live="polite">
          <div className="progress-header">
            <strong>{phaseLabel(pipelinePhase)}</strong>
            <span>{elapsedSeconds}s elapsed</span>
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <ul className="progress-steps">
            <li className={isSyncing || syncSummary ? 'step-active' : ''}>1. Sync SourceForge trunk</li>
            <li className={isIndexing || ingestStats ? 'step-active' : ''}>2. Index and embed corpus</li>
            <li className={pipelinePhase === 'completed' ? 'step-active' : ''}>3. Ready for queries</li>
          </ul>
        </div>
      ) : null}

      <div>
        {ingestError ? <p role="alert">Indexing issue: {ingestError}</p> : null}
        {syncSummary ? <p>{syncSummary}</p> : null}
        {ingestStats ? (
          <>
            <p>{formatIngestSummary(ingestStats, lastIngestMode)}</p>
            <ul className="health-list">
                <li>Mode: {ingestStats.mode}</li>
                <li>Started: {new Date(ingestStats.started_at).toLocaleString()}</li>
                <li>Completed: {new Date(ingestStats.completed_at).toLocaleString()}</li>
                <li>Duration: {formatDuration(ingestStats.duration_seconds)}</li>
                <li>Corpus LOC: {ingestStats.corpus_loc}</li>
                <li>
                  Time per 10,000 LOC: {formatSecondsPerTenThousandLoc(ingestStats.duration_seconds, ingestStats.corpus_loc)}
                </li>
                <li>Corpus size: {formatBytes(ingestStats.corpus_bytes)}</li>
              </ul>
          </>
        ) : null}
        {skipWarning ? (
          <div className="warning-panel">
            <p>{skipWarning}</p>
            <button className="secondary-button" onClick={() => onIngestClick('full')} disabled={isBusy}>
              Reindex now
            </button>
          </div>
        ) : null}
      </div>
    </section>
  )
}
