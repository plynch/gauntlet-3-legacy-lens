from app.core.settings import Settings
from app.services.query_service import QueryService
from app.services.types import SearchHit


class FakeQdrantGateway:
    def __init__(self, hits: list[SearchHit]) -> None:
        self._hits = hits

    def search(self, collection_name: str, vector: list[float], limit: int) -> list[SearchHit]:
        return self._hits[:limit]


class FakeOpenAIGateway:
    def __init__(self, answer_text: str = "Answer from model") -> None:
        self._answer_text = answer_text

    def embed_texts(self, texts: list[str], model: str) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

    def generate_answer(self, question: str, hits: list[SearchHit], model: str, max_context_characters: int) -> str:
        return self._answer_text


def test_query_service_returns_snippets_and_citations() -> None:
    settings = Settings()
    hits = [
        SearchHit(
            text="READ CUSTOMER-FILE",
            score=0.98,
            source_path="sample.cbl",
            line_start=12,
            line_end=16,
            section="READ-CUSTOMER",
        )
    ]
    service = QueryService(
        settings=settings,
        qdrant=FakeQdrantGateway(hits=hits),  # type: ignore[arg-type]
        openai_gateway=FakeOpenAIGateway(),
    )

    response = service.answer("Where is file IO handled?")

    assert response.insufficient_evidence is False
    assert response.answer == "Answer from model"
    assert len(response.snippets) == 1
    assert response.citations[0].path == "sample.cbl"


def test_query_service_handles_empty_retrieval() -> None:
    settings = Settings()
    service = QueryService(
        settings=settings,
        qdrant=FakeQdrantGateway(hits=[]),  # type: ignore[arg-type]
        openai_gateway=FakeOpenAIGateway(),
    )

    response = service.answer("Unknown question")

    assert response.insufficient_evidence is True
    assert response.snippets == []
    assert response.citations == []
