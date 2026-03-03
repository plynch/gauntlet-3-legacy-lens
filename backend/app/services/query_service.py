from app.core.settings import Settings
from app.models.query import Citation, QueryResponse, RetrievedSnippet
from app.services.openai_gateway import OpenAIGateway
from app.services.qdrant_gateway import QdrantGateway


class QueryService:
    def __init__(self, settings: Settings, qdrant: QdrantGateway, openai_gateway: OpenAIGateway) -> None:
        self._settings = settings
        self._qdrant = qdrant
        self._openai_gateway = openai_gateway

    def answer(self, question: str, top_k: int | None = None) -> QueryResponse:
        effective_top_k = top_k or self._settings.query_top_k

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

        return QueryResponse(
            question=question,
            answer=answer,
            insufficient_evidence=False,
            snippets=snippets,
            citations=citations,
        )
