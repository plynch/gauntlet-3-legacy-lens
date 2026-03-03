from datetime import datetime

from pydantic import BaseModel


class IngestStats(BaseModel):
    mode: str = "incremental"
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    files_seen: int
    files_indexed: int
    files_skipped: int
    chunks_indexed: int
    corpus_bytes: int
    corpus_loc: int
