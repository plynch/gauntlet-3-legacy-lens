import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ServiceStatusPanel } from './ServiceStatusPanel'
import * as api from '../lib/api'
import type { IngestStats, IngestStatus } from '../lib/api'

vi.mock('../lib/api', async () => {
  const actual = await vi.importActual<typeof import('../lib/api')>('../lib/api')
  return {
    ...actual,
    areIngestControlsEnabled: vi.fn(() => true),
    getIngestStatus: vi.fn(),
    runIngest: vi.fn(),
    syncSourceForge: vi.fn(),
  }
})

function createDeferred<T>() {
  let resolveFn: (value: T) => void = () => undefined
  let rejectFn: (reason?: unknown) => void = () => undefined
  const promise = new Promise<T>((resolve, reject) => {
    resolveFn = resolve
    rejectFn = reject
  })
  return {
    promise,
    resolve: resolveFn,
    reject: rejectFn,
  }
}

function makeIngestStatus(overrides: Partial<IngestStatus> = {}): IngestStatus {
  return {
    active: false,
    phase: 'idle',
    mode: null,
    started_at: null,
    updated_at: '2026-03-04T18:00:00Z',
    sync_started_at: null,
    sync_completed_at: null,
    sync_files_synced: null,
    sync_corpus_loc: null,
    sync_corpus_bytes: null,
    ingest_stats: null,
    last_indexed_at: null,
    has_indexed_data: false,
    summary: null,
    error: null,
    error_stage: null,
    ...overrides,
  }
}

function makeStats(overrides: Partial<IngestStats> = {}): IngestStats {
  return {
    mode: 'incremental',
    started_at: '2026-03-04T18:00:00Z',
    completed_at: '2026-03-04T18:00:02Z',
    duration_seconds: 2,
    files_seen: 2,
    files_indexed: 2,
    files_skipped: 0,
    files_unchanged: 0,
    files_not_indexable: 0,
    chunks_indexed: 9,
    corpus_bytes: 2048,
    corpus_loc: 120,
    skipped_paths: [],
    ...overrides,
  }
}

const getIngestStatusMock = vi.mocked(api.getIngestStatus)
const runIngestMock = vi.mocked(api.runIngest)

describe('ServiceStatusPanel ingest transitions', () => {
  beforeEach(() => {
    getIngestStatusMock.mockResolvedValue(makeIngestStatus())
  })

  it('shows indexing state and then success summary for incremental ingest', async () => {
    const completedStats = makeStats()
    const deferred = createDeferred<IngestStats>()

    getIngestStatusMock
      .mockResolvedValueOnce(makeIngestStatus())
      .mockResolvedValue(
        makeIngestStatus({
          phase: 'completed',
          mode: 'incremental',
          ingest_stats: completedStats,
          has_indexed_data: true,
          last_indexed_at: completedStats.completed_at,
        }),
      )
    runIngestMock.mockReturnValueOnce(deferred.promise)

    render(
      <ServiceStatusPanel
        health={{
          status: 'ok',
          service: 'LegacyLens API (Test)',
          timestamp: '2026-03-04T18:00:00Z',
          qdrant_configured: true,
        }}
        healthLoading={false}
        healthError=""
        onRefreshHealth={vi.fn()}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Index changes' }))
    expect(await screen.findByRole('button', { name: 'Indexing changes...' })).toBeDisabled()

    deferred.resolve(completedStats)

    await waitFor(() => {
      expect(screen.getByText('Indexed 2/2 files and 9 chunks.')).toBeInTheDocument()
    })
  })

  it('surfaces an ingest error when reindex fails', async () => {
    getIngestStatusMock.mockResolvedValue(
      makeIngestStatus({
        phase: 'failed',
        mode: 'full',
        error: 'network timeout',
        error_stage: 'indexing',
      }),
    )
    runIngestMock.mockRejectedValueOnce(new Error('network timeout'))

    render(
      <ServiceStatusPanel
        health={{
          status: 'ok',
          service: 'LegacyLens API (Test)',
          timestamp: '2026-03-04T18:00:00Z',
          qdrant_configured: true,
        }}
        healthLoading={false}
        healthError=""
        onRefreshHealth={vi.fn()}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Reindex all' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Indexing issue: network timeout')
    })
    expect(screen.getByText('Ingest failed')).toBeInTheDocument()
  })
})
