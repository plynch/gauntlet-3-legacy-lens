from pydantic import BaseModel


class IngestStats(BaseModel):
    files_seen: int
    files_indexed: int
    files_skipped: int
    chunks_indexed: int
