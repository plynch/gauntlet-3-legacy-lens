import { useEffect, useMemo, useState } from 'react'
import { HealthResponse, IngestStats, areIngestControlsEnabled, getIngestRuns, runIngest, syncSourceForge } from '../lib/api'

type IngestMode = 'full' | 'incremental'
type PipelinePhase = 'idle' | 'syncing' | 'indexing' | 'completed' | 'failed'

type ServiceStatusPanelProps = {
  health: HealthResponse | null
  healthLoading: boolean
  healthError: string
  onRefreshHealth: () => Promise<void> | void
}

function ingestBuckets(stats: IngestStats) {
  let unchanged = stats.files_unchanged ?? 0
  let notIndexable = stats.files_not_indexable ?? 0
  if (unchanged === 0 && notIndexable === 0 && stats.files_skipped > 0) {
    if (stats.mode === 'incremental') {
      unchanged = stats.files_skipped
    } else {
      notIndexable = stats.files_skipped
    }
  }
  const otherNonIndexed = Math.max(0, stats.files_skipped - unchanged - notIndexable)
  return { unchanged, notIndexable, otherNonIndexed }
}

function formatIngestSummary(stats: IngestStats, mode: IngestMode | null): string {
  if (stats.files_seen === 0) {
    return 'No source files were discovered in configured source directories.'
  }

  const { unchanged, notIndexable, otherNonIndexed } = ingestBuckets(stats)

  if (stats.files_indexed === 0 && stats.files_skipped === stats.files_seen) {
    if (mode === 'incremental') {
      return `No changed files detected. ${unchanged}/${stats.files_seen} files were unchanged.`
    }

    if (notIndexable === stats.files_seen) {
      return `No indexable content found. ${notIndexable}/${stats.files_seen} files were empty or not chunkable.`
    }

    return `No chunks were indexed. ${stats.files_skipped}/${stats.files_seen} files were not indexed.`
  }

  const details: string[] = []
  if (unchanged > 0) details.push(`${unchanged} unchanged`)
  if (notIndexable > 0) details.push(`${notIndexable} not indexable`)
  if (otherNonIndexed > 0) details.push(`${otherNonIndexed} not indexed`)
  if (details.length > 0) {
    return `Indexed ${stats.files_indexed}/${stats.files_seen} files and ${stats.chunks_indexed} chunks (${details.join(', ')}).`
  }

  return `Indexed ${stats.files_indexed}/${stats.files_seen} files and ${stats.chunks_indexed} chunks.`
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

  const nonIndexableInfo = useMemo(() => {
    if (!ingestStats) return null
    const { notIndexable } = ingestBuckets(ingestStats)
    if (notIndexable === 0) return null
    return `${notIndexable} file(s) had no indexable content (for example empty placeholders).`
  }, [ingestStats])

  const nonIndexablePaths = useMemo(() => {
    return (ingestStats?.skipped_paths ?? []).filter((path) => path.includes('no indexable content')).slice(0, 3)
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
    const syncStartedLabel = new Date().toLocaleString()
    setIngestLoadingMode('full')
    setLastIngestMode('full')
    setIngestError('')
    setIngestStats(null)
    setSyncSummary(`Began SourceForge sync at ${syncStartedLabel}.`)
    setPipelinePhase('syncing')
    setOperationStartedAt(Date.now())
    setElapsedSeconds(0)

    try {
      const syncStats = await syncSourceForge()
      setSyncSummary(
        `Began SourceForge sync at ${syncStartedLabel}. Finished SourceForge sync (${syncStats.files_synced} files, ${syncStats.corpus_loc} LOC) at ${new Date(syncStats.synced_at).toLocaleString()}. Full indexing is now running.`,
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
  const ingestBreakdown = ingestStats ? ingestBuckets(ingestStats) : null
  const ingestControlsEnabled = areIngestControlsEnabled()

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

      {ingestControlsEnabled ? (
        <>
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
          <p className="muted-note">Full ingest can take 5-10 minutes for the current GnuCOBOL trunk (~572K LOC).</p>

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
                    Time per 10,000 LOC:{' '}
                    {formatSecondsPerTenThousandLoc(ingestStats.duration_seconds, ingestStats.corpus_loc)}
                  </li>
                  <li>Corpus size: {formatBytes(ingestStats.corpus_bytes)}</li>
                  {ingestBreakdown?.unchanged ? <li>Unchanged files: {ingestBreakdown.unchanged}</li> : null}
                  {ingestBreakdown?.notIndexable ? (
                    <li>Not indexable files: {ingestBreakdown.notIndexable} (for example empty placeholders)</li>
                  ) : null}
                  {ingestBreakdown?.otherNonIndexed ? <li>Other non-indexed files: {ingestBreakdown.otherNonIndexed}</li> : null}
                </ul>
              </>
            ) : null}
            {nonIndexableInfo ? (
              <div className="info-panel">
                <p>{nonIndexableInfo}</p>
                {nonIndexablePaths.length ? (
                  <ul className="health-list">
                    {nonIndexablePaths.map((path) => (
                      <li key={path}>{path}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}
          </div>
        </>
      ) : (
        <p className="muted-note">
          Ingest controls are disabled in this deployment. Use API or CLI ingest for controlled indexing workflows.
        </p>
      )}
    </section>
  )
}
