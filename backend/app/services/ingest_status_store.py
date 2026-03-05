from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Literal

from app.models.corpus import SourceForgeSyncStats
from app.models.ingest import IngestStats, IngestStatus
from app.services.ingest_benchmarks import read_ingest_runs

IngestMode = Literal["full", "incremental"]
PipelinePhase = Literal["idle", "syncing", "indexing", "completed", "failed"]
ErrorStage = Literal["sync", "indexing"]


class IngestStatusStore:
    def __init__(self) -> None:
        now = _utc_now()
        self._lock = Lock()
        self._status = IngestStatus(updated_at=now)

    def snapshot(self, benchmark_log_path: str | None = None) -> IngestStatus:
        fallback_last_indexed_at = self._read_last_indexed_at(benchmark_log_path)
        with self._lock:
            if self._status.last_indexed_at is None and fallback_last_indexed_at is not None:
                self._status.last_indexed_at = fallback_last_indexed_at
                self._status.has_indexed_data = True
                self._status.updated_at = _utc_now()
            return self._status.model_copy(deep=True)

    def try_begin(self, *, mode: IngestMode, phase: PipelinePhase, summary: str | None = None) -> bool:
        with self._lock:
            if self._status.active:
                return False
            now = _utc_now()
            self._status.active = True
            self._status.phase = phase
            self._status.mode = mode
            self._status.started_at = now
            self._status.updated_at = now
            self._status.sync_started_at = now if phase == "syncing" else None
            self._status.sync_completed_at = None
            self._status.sync_files_synced = None
            self._status.sync_corpus_loc = None
            self._status.sync_corpus_bytes = None
            self._status.ingest_stats = None
            self._status.error = None
            self._status.error_stage = None
            self._status.summary = summary
            return True

    def mark_sync_completed(self, sync: SourceForgeSyncStats, summary: str | None = None) -> None:
        with self._lock:
            self._status.phase = "syncing"
            self._status.sync_completed_at = sync.synced_at
            self._status.sync_files_synced = sync.files_synced
            self._status.sync_corpus_loc = sync.corpus_loc
            self._status.sync_corpus_bytes = sync.corpus_bytes
            self._status.updated_at = _utc_now()
            if summary is not None:
                self._status.summary = summary

    def mark_indexing_started(self, summary: str | None = None) -> None:
        with self._lock:
            self._status.phase = "indexing"
            self._status.updated_at = _utc_now()
            if summary is not None:
                self._status.summary = summary

    def mark_completed(self, ingest_stats: IngestStats, summary: str | None = None) -> None:
        with self._lock:
            self._status.active = False
            self._status.phase = "completed"
            self._status.ingest_stats = ingest_stats
            self._status.last_indexed_at = ingest_stats.completed_at
            self._status.has_indexed_data = True
            self._status.error = None
            self._status.error_stage = None
            self._status.updated_at = _utc_now()
            if summary is not None:
                self._status.summary = summary

    def mark_indexed_data_detected(self, last_indexed_at: datetime | None = None) -> None:
        with self._lock:
            if self._status.has_indexed_data and (self._status.last_indexed_at is not None or last_indexed_at is None):
                return
            self._status.has_indexed_data = True
            if self._status.last_indexed_at is None and last_indexed_at is not None:
                self._status.last_indexed_at = last_indexed_at
            self._status.updated_at = _utc_now()

    def mark_failed(self, *, error: str, stage: ErrorStage, summary: str | None = None) -> None:
        with self._lock:
            self._status.active = False
            self._status.phase = "failed"
            self._status.error = error
            self._status.error_stage = stage
            self._status.updated_at = _utc_now()
            if summary is not None:
                self._status.summary = summary

    def mark_sync_only_completed(self, sync: SourceForgeSyncStats, summary: str | None = None) -> None:
        with self._lock:
            self._status.active = False
            self._status.phase = "completed"
            self._status.sync_completed_at = sync.synced_at
            self._status.sync_files_synced = sync.files_synced
            self._status.sync_corpus_loc = sync.corpus_loc
            self._status.sync_corpus_bytes = sync.corpus_bytes
            self._status.error = None
            self._status.error_stage = None
            self._status.updated_at = _utc_now()
            if summary is not None:
                self._status.summary = summary

    def _read_last_indexed_at(self, benchmark_log_path: str | None) -> datetime | None:
        if not benchmark_log_path:
            return None
        try:
            runs = read_ingest_runs(benchmark_log_path, limit=1)
        except OSError:
            return None
        if not runs:
            return None
        return runs[0].completed_at


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


ingest_status_store = IngestStatusStore()
