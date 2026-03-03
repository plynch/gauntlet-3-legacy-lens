from app.core.settings import Settings
from app.models.query import Citation, QueryResponse, RetrievedSnippet
from app.services.openai_gateway import OpenAIGateway
from app.services.qdrant_gateway import QdrantGateway
from app.services.tracing import LangfuseTracer


class QueryService:
    def __init__(
        self,
        settings: Settings,
        qdrant: QdrantGateway,
        openai_gateway: OpenAIGateway,
        tracer: LangfuseTracer | None = None,
    ) -> None:
        self._settings = settings
        self._qdrant = qdrant
        self._openai_gateway = openai_gateway
        self._tracer = tracer or getattr(openai_gateway, "tracer", None)

    def answer(self, question: str, top_k: int | None = None) -> QueryResponse:
        effective_top_k = top_k or self._settings.query_top_k

        with self._query_trace(question=question, top_k=effective_top_k) as trace:
            try:
                query_vector = self._openai_gateway.embed_texts([question], model=self._settings.embedding_model)[0]
                hits = self._qdrant.search(
                    collection_name=self._settings.qdrant_collection,
                    vector=query_vector,
                    limit=effective_top_k,
                )
            except RuntimeError:
                hits = []

            if not hits:
                trace.update(output={"hit_count": 0, "insufficient_evidence": True})
                return QueryResponse(
                    question=question,
                    answer="I could not find enough evidence in the indexed corpus to answer this question.",
                    insufficient_evidence=True,
                    snippets=[],
                    citations=[],
                )

            answer = self._openai_gateway.generate_answer(
                question=question,
                hits=hits,
                model=self._settings.generation_model,
                max_context_characters=self._settings.max_context_characters,
            )
            snippets = [
                RetrievedSnippet(
                    text=hit.text,
                    score=hit.score,
                    citation=Citation(
                        path=hit.source_path,
                        line_start=hit.line_start,
                        line_end=hit.line_end,
                        section=hit.section,
                    ),
                )
                for hit in hits
            ]
            citations = [snippet.citation for snippet in snippets]
            response = QueryResponse(
                question=question,
                answer=answer,
                insufficient_evidence=False,
                snippets=snippets,
                citations=citations,
            )
            trace.update(
                output={
                    "hit_count": len(hits),
                    "insufficient_evidence": False,
                    "citation_count": len(citations),
                    "answer_preview": answer[:500],
                }
            )
            return response

    def _query_trace(self, *, question: str, top_k: int):
        if not self._tracer:
            return _NullTraceContext()
        return self._tracer.span(
            name="query.answer",
            input={"question": question, "top_k": top_k},
            metadata={
                "embedding_model": self._settings.embedding_model,
                "generation_model": self._settings.generation_model,
                "collection": self._settings.qdrant_collection,
            },
        )


class _NullTraceContext:
    def __enter__(self):
        return _NullTrace()

    def __exit__(self, exc_type, exc, tb):
        return False


class _NullTrace:
    def update(self, **kwargs: object) -> None:  # pragma: no cover - trivial no-op
        return
