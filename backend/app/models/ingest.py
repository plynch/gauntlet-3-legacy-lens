from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class IngestStats(BaseModel):
    mode: str = "incremental"
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    files_seen: int
    files_indexed: int
    files_skipped: int
    files_unchanged: int = 0
    files_not_indexable: int = 0
    chunks_indexed: int
    corpus_bytes: int
    corpus_loc: int
    skipped_paths: list[str] = Field(default_factory=list)


class IngestStatus(BaseModel):
    active: bool = False
    phase: Literal["idle", "syncing", "indexing", "completed", "failed"] = "idle"
    mode: Literal["full", "incremental"] | None = None
    started_at: datetime | None = None
    updated_at: datetime
    sync_started_at: datetime | None = None
    sync_completed_at: datetime | None = None
    sync_files_synced: int | None = None
    sync_corpus_loc: int | None = None
    sync_corpus_bytes: int | None = None
    ingest_stats: IngestStats | None = None
    last_indexed_at: datetime | None = None
    has_indexed_data: bool = False
    summary: str | None = None
    error: str | None = None
    error_stage: Literal["sync", "indexing"] | None = None
