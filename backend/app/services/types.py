from dataclasses import dataclass


@dataclass(slots=True)
class SourceFile:
    path: str
    text: str
    sha1: str


@dataclass(slots=True)
class SourceChunk:
    id: str
    text: str
    source_path: str
    file_hash: str
    line_start: int
    line_end: int
    section: str | None


@dataclass(slots=True)
class SearchHit:
    text: str
    score: float
    source_path: str
    line_start: int
    line_end: int
    section: str | None
