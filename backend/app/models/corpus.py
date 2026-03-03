from datetime import datetime

from pydantic import BaseModel

from app.models.ingest import IngestStats


class SourceForgeSyncStats(BaseModel):
    source_url: str
    destination_path: str
    synced_at: datetime
    files_synced: int
    corpus_loc: int
    corpus_bytes: int


class SourceForgeFullIngestResponse(BaseModel):
    sync: SourceForgeSyncStats
    ingest: IngestStats
