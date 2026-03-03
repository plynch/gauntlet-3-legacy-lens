from contextlib import contextmanager

from fastapi.testclient import TestClient

import app.api.query as query_api
from app.main import app
from app.models.ingest import IngestStats
from app.models.query import Citation, QueryResponse, RetrievedSnippet

client = TestClient(app)


class FakeQueryService:
    def __init__(self, response: QueryResponse) -> None:
        self._response = response

    def answer(self, question: str, top_k: int | None = None) -> QueryResponse:
        return self._response


class FakeIngestionService:
    def __init__(self, stats: IngestStats) -> None:
        self._stats = stats

    def ingest(self, mode: str = "incremental") -> IngestStats:
        return self._stats


@contextmanager
def fake_runtime_services(_settings: object):
    yield type("Runtime", (), {"settings": query_api.settings, "qdrant": object(), "openai_gateway": object()})()


def test_post_query_route_returns_contract(monkeypatch) -> None:
    response_payload = QueryResponse(
        question="Where is file IO handled?",
        answer="File IO is handled in OPEN-FILES and READ-CUSTOMER.",
        insufficient_evidence=False,
        snippets=[
            RetrievedSnippet(
                text="OPEN INPUT CUSTOMER-FILE",
                score=0.9,
                citation=Citation(
                    path="data/corpus/customer_accounts.cbl",
                    line_start=35,
                    line_end=37,
                    section="OPEN-FILES",
                ),
            )
        ],
        citations=[
            Citation(
                path="data/corpus/customer_accounts.cbl",
                line_start=35,
                line_end=37,
                section="OPEN-FILES",
            )
        ],
    )

    monkeypatch.setattr(query_api, "runtime_services", fake_runtime_services)
    monkeypatch.setattr(query_api, "QueryService", lambda **_: FakeQueryService(response_payload))

    response = client.post("/api/query", json={"question": "Where is file IO handled?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["insufficient_evidence"] is False
    assert payload["answer"]
    assert payload["citations"][0]["path"].endswith("customer_accounts.cbl")


def test_post_ingest_route_returns_stats(monkeypatch) -> None:
    stats_payload = IngestStats(files_seen=10, files_indexed=8, files_skipped=2, chunks_indexed=42)

    monkeypatch.setattr(query_api, "runtime_services", fake_runtime_services)
    monkeypatch.setattr(query_api, "IngestionService", lambda **_: FakeIngestionService(stats_payload))

    response = client.post("/api/ingest?mode=incremental")

    assert response.status_code == 200
    payload = response.json()
    assert payload["files_seen"] == 10
    assert payload["chunks_indexed"] == 42
