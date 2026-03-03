import { IngestStats } from '../lib/api'

export type IngestMode = 'full' | 'incremental'
export type PipelinePhase = 'idle' | 'syncing' | 'indexing' | 'completed' | 'failed'

export function ingestBuckets(stats: IngestStats) {
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

export function formatIngestSummary(stats: IngestStats, mode: IngestMode | null): string {
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

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(2)}s`
  }
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds - minutes * 60
  return `${minutes}m ${remainder.toFixed(2)}s`
}

export function formatSecondsPerTenThousandLoc(durationSeconds: number, corpusLoc: number): string {
  if (corpusLoc <= 0) {
    return 'n/a'
  }
  const secondsPerTenThousand = (durationSeconds * 10000) / corpusLoc
  return formatDuration(secondsPerTenThousand)
}

export function phaseLabel(phase: PipelinePhase): string {
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

export function progressPercent(phase: PipelinePhase, elapsedSeconds: number): number {
  if (phase === 'idle') return 0
  if (phase === 'syncing') return Math.min(35, 8 + elapsedSeconds * 2)
  if (phase === 'indexing') return Math.min(95, 35 + elapsedSeconds * 0.45)
  if (phase === 'completed') return 100
  return 100
}
