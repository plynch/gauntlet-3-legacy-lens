from datetime import datetime

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
