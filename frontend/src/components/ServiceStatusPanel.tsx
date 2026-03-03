import { useEffect, useState } from 'react'
import {
  HealthResponse,
  IngestStats,
  IngestStatus,
  areIngestControlsEnabled,
  getIngestStatus,
  runIngest,
  syncSourceForge,
} from '../lib/api'
import {
  IngestMode,
  PipelinePhase,
  formatBytes,
  formatDuration,
  formatIngestSummary,
  formatSecondsPerTenThousandLoc,
  ingestBuckets,
  phaseLabel,
  progressPercent,
} from './serviceStatusUtils'

type ServiceStatusPanelProps = {
  health: HealthResponse | null
  healthLoading: boolean
  healthError: string
  onRefreshHealth: () => Promise<void> | void
}

export function ServiceStatusPanel(props: ServiceStatusPanelProps) {
  const { health, healthError, healthLoading, onRefreshHealth } = props
  const [ingestLoadingMode, setIngestLoadingMode] = useState<IngestMode | null>(null)
  const [ingestError, setIngestError] = useState('')
  const [ingestStats, setIngestStats] = useState<IngestStats | null>(null)
  const [lastIngestMode, setLastIngestMode] = useState<IngestMode | null>(null)
  const [syncSummary, setSyncSummary] = useState('')
  const [pipelinePhase, setPipelinePhase] = useState<PipelinePhase>('idle')
  const [operationStartedAt, setOperationStartedAt] = useState<number | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [lastIndexedAt, setLastIndexedAt] = useState<string | null>(null)
  const [statusLoaded, setStatusLoaded] = useState(false)

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
    let intervalId: number | undefined
    async function pollIngestStatus() {
      try {
        const status = await getIngestStatus()
        if (cancelled) return
        hydrateFromSharedStatus(status)
        setStatusLoaded(true)
      } catch {
        // Status polling should not block query UX.
      }
    }

    pollIngestStatus()
    intervalId = window.setInterval(() => {
      void pollIngestStatus()
    }, 3000)

    return () => {
      cancelled = true
      if (intervalId !== undefined) {
        window.clearInterval(intervalId)
      }
    }
  }, [])

  function hydrateFromSharedStatus(status: IngestStatus) {
    setPipelinePhase(status.phase)
    setLastIngestMode(status.mode)
    setIngestStats(status.ingest_stats)
    setIngestError(status.error || '')
    setSyncSummary(status.summary || '')
    setLastIndexedAt(status.last_indexed_at || status.ingest_stats?.completed_at || null)

    if (status.active && status.started_at) {
      const startedAtMs = new Date(status.started_at).getTime()
      if (!Number.isNaN(startedAtMs)) {
        setOperationStartedAt(startedAtMs)
        setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startedAtMs) / 1000)))
      }
    } else {
      setOperationStartedAt(null)
      setElapsedSeconds(0)
    }

    setIngestLoadingMode(status.active ? status.mode : null)
  }

  async function refreshSharedStatus() {
    try {
      const status = await getIngestStatus()
      hydrateFromSharedStatus(status)
      setStatusLoaded(true)
    } catch {
      // Keep existing state when status endpoint is temporarily unavailable.
    }
  }

  const nonIndexableCount = ingestStats ? ingestBuckets(ingestStats).notIndexable : 0
  const nonIndexableInfo =
    nonIndexableCount > 0 ? `${nonIndexableCount} file(s) had no indexable content (for example empty placeholders).` : null
  const nonIndexablePaths = (ingestStats?.skipped_paths ?? []).filter((path) => path.includes('no indexable content')).slice(0, 3)

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
      void refreshSharedStatus()
    }
  }

  async function onSourceForgeFullIngestClick() {
    const syncStartedLabel = new Date().toLocaleString()
    let syncFinishedLabel: string | null = null
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
      syncFinishedLabel = new Date(syncStats.synced_at).toLocaleString()
      setSyncSummary(
        `Began SourceForge sync at ${syncStartedLabel}. Finished SourceForge sync (${syncStats.files_synced} files, ${syncStats.corpus_loc} LOC) at ${syncFinishedLabel}. Starting full indexing.`,
      )
      setPipelinePhase('indexing')
      const stats = await runIngest('full')
      setIngestStats(stats)
      setLastIndexedAt(stats.completed_at)
      setPipelinePhase('completed')
      setSyncSummary(
        `Began SourceForge sync at ${syncStartedLabel}. Finished SourceForge sync (${syncStats.files_synced} files, ${syncStats.corpus_loc} LOC) at ${syncFinishedLabel}. Full indexing completed at ${new Date(stats.completed_at).toLocaleString()}.`,
      )
    } catch (err: unknown) {
      setPipelinePhase('failed')
      if (syncFinishedLabel) {
        setSyncSummary(
          `Began SourceForge sync at ${syncStartedLabel}. Finished SourceForge sync at ${syncFinishedLabel}. Full indexing failed before completion.`,
        )
      } else {
        setSyncSummary(`Began SourceForge sync at ${syncStartedLabel}. SourceForge sync failed before completion.`)
      }
      setIngestError(err instanceof Error ? err.message : 'SourceForge sync + reindex failed')
    } finally {
      setIngestLoadingMode(null)
      void refreshSharedStatus()
    }
  }

  const progress = progressPercent(pipelinePhase, elapsedSeconds)
  const isBusy = ingestLoadingMode !== null
  const isSyncing = pipelinePhase === 'syncing'
  const isIndexing = pipelinePhase === 'indexing'
  const ingestBreakdown = ingestStats ? ingestBuckets(ingestStats) : null
  const ingestControlsEnabled = areIngestControlsEnabled()
  const lastIndexedLabel = lastIndexedAt ? new Date(lastIndexedAt).toLocaleString() : statusLoaded ? 'not yet indexed' : 'loading...'

  return (
    <section className="status-panel">
      <h2 className="status-heading">Service Status</h2>
      {healthLoading ? (
        <p className="status-message">Checking backend health...</p>
      ) : healthError ? (
        <p className="status-message status-error" role="alert">
          Backend issue: {healthError}
        </p>
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
            <div className="ingest-secondary-actions">
              <button onClick={() => onIngestClick('incremental')} disabled={isBusy}>
                {isIndexing && lastIngestMode === 'incremental' ? 'Indexing changes...' : 'Index changes'}
              </button>
              <button className="secondary-button" onClick={() => onIngestClick('full')} disabled={isBusy}>
                {isIndexing && lastIngestMode === 'full' ? 'Reindexing...' : 'Reindex all'}
              </button>
              <button className="secondary-button" onClick={onRefreshHealth} disabled={healthLoading || isBusy}>
                {healthLoading ? 'Refreshing...' : 'Refresh health'}
              </button>
            </div>
          </div>
          <p className="last-indexed-note">Last indexed at: {lastIndexedLabel}</p>

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

          {ingestError ? (
            <p className="status-message status-error" role="alert">
              Indexing issue: {ingestError}
            </p>
          ) : null}
          {syncSummary ? <p className="status-message">{syncSummary}</p> : null}
          {ingestStats ? (
            <>
              <p className="status-message">{formatIngestSummary(ingestStats, lastIngestMode)}</p>
              <ul className="health-list">
                <li>Mode: {ingestStats.mode}</li>
                <li>Started: {new Date(ingestStats.started_at).toLocaleString()}</li>
                <li>Completed: {new Date(ingestStats.completed_at).toLocaleString()}</li>
                <li>Duration: {formatDuration(ingestStats.duration_seconds)}</li>
                <li>Corpus LOC: {ingestStats.corpus_loc}</li>
                <li>Time per 10,000 LOC: {formatSecondsPerTenThousandLoc(ingestStats.duration_seconds, ingestStats.corpus_loc)}</li>
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
        </>
      ) : (
        <p className="status-message muted-note">
          Ingest controls are disabled in this deployment. Use API or CLI ingest for controlled indexing workflows.
        </p>
      )}
    </section>
  )
}
