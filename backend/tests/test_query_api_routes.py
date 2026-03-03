from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi.testclient import TestClient

import app.api.query as query_api
from app.main import app
from app.models.corpus import SourceForgeSyncStats
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
    stats_payload = IngestStats(
        mode="incremental",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_seconds=1.2,
        files_seen=10,
        files_indexed=8,
        files_skipped=2,
        chunks_indexed=42,
        corpus_bytes=2048,
        corpus_loc=120,
    )

    monkeypatch.setattr(query_api, "runtime_services", fake_runtime_services)
    monkeypatch.setattr(query_api, "IngestionService", lambda **_: FakeIngestionService(stats_payload))

    response = client.post("/api/ingest?mode=incremental")

    assert response.status_code == 200
    payload = response.json()
    assert payload["files_seen"] == 10
    assert payload["chunks_indexed"] == 42
    assert payload["corpus_loc"] == 120


def test_get_ingest_runs_route_returns_history(monkeypatch) -> None:
    stats_payload = IngestStats(
        mode="full",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_seconds=2.4,
        files_seen=2,
        files_indexed=2,
        files_skipped=0,
        chunks_indexed=11,
        corpus_bytes=4096,
        corpus_loc=300,
    )
    monkeypatch.setattr(query_api, "read_ingest_runs", lambda _path, limit=20: [stats_payload])

    response = client.get("/api/ingest/runs?limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["mode"] == "full"
    assert payload[0]["corpus_bytes"] == 4096


def test_sync_sourceforge_route_returns_stats(monkeypatch) -> None:
    sync_payload = SourceForgeSyncStats(
        source_url="https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/",
        destination_path="data/corpus/sourceforge-trunk",
        synced_at=datetime.now(timezone.utc),
        files_synced=50,
        corpus_loc=10000,
        corpus_bytes=200000,
    )
    monkeypatch.setattr(query_api, "sync_sourceforge_trunk", lambda *_args, **_kwargs: sync_payload)

    response = client.post("/api/corpus/sourceforge/sync")

    assert response.status_code == 200
    payload = response.json()
    assert payload["files_synced"] == 50
    assert payload["corpus_loc"] == 10000


def test_sourceforge_full_ingest_route_returns_sync_and_ingest(monkeypatch) -> None:
    sync_payload = SourceForgeSyncStats(
        source_url="https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/",
        destination_path="data/corpus/sourceforge-trunk",
        synced_at=datetime.now(timezone.utc),
        files_synced=50,
        corpus_loc=10000,
        corpus_bytes=200000,
    )
    ingest_payload = IngestStats(
        mode="full",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_seconds=12.3,
        files_seen=50,
        files_indexed=50,
        files_skipped=0,
        chunks_indexed=1234,
        corpus_bytes=200000,
        corpus_loc=10000,
    )
    monkeypatch.setattr(query_api, "sync_sourceforge_trunk", lambda *_args, **_kwargs: sync_payload)
    monkeypatch.setattr(query_api, "runtime_services", fake_runtime_services)
    monkeypatch.setattr(query_api, "IngestionService", lambda **_: FakeIngestionService(ingest_payload))

    response = client.post("/api/corpus/sourceforge/full-ingest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sync"]["files_synced"] == 50
    assert payload["ingest"]["chunks_indexed"] == 1234


def test_get_features_route_returns_catalog() -> None:
    response = client.get("/api/features")

    assert response.status_code == 200
    payload = response.json()
    keys = {item["key"] for item in payload["features"]}
    assert "code_explanation" in keys
    assert "dependency_mapping" in keys


def test_post_feature_query_route_uses_feature_question(monkeypatch) -> None:
    response_payload = QueryResponse(
        question="Explain section READ-CUSTOMER",
        answer="READ-CUSTOMER handles file reads with EOF checks.",
        insufficient_evidence=False,
        snippets=[],
        citations=[],
    )
    captured: dict[str, str] = {}

    class CapturingQueryService(FakeQueryService):
        def answer(self, question: str, top_k: int | None = None) -> QueryResponse:
            captured["question"] = question
            return response_payload

    monkeypatch.setattr(query_api, "runtime_services", fake_runtime_services)
    monkeypatch.setattr(query_api, "QueryService", lambda **_: CapturingQueryService(response_payload))

    response = client.post("/api/features/code_explanation/query", json={"subject": "READ-CUSTOMER"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"]
    assert "READ-CUSTOMER" in captured["question"]
