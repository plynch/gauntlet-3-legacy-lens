from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class Citation(BaseModel):
    path: str
    line_start: int
    line_end: int
    section: str | None = None


class RetrievedSnippet(BaseModel):
    text: str
    score: float
    citation: Citation


class QueryResponse(BaseModel):
    question: str
    answer: str
    insufficient_evidence: bool
    snippets: list[RetrievedSnippet]
    citations: list[Citation]
