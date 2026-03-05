from contextlib import contextmanager
from datetime import datetime

from app.models.ingest import IngestStats
from app.models.query import QueryResponse


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


class FakeStatusQdrantGateway:
    def __init__(self, *, latest_indexed_at: datetime | None = None, has_any_points: bool = False) -> None:
        self._latest_indexed_at = latest_indexed_at
        self._has_any_points = has_any_points

    def get_latest_indexed_at(self, collection_name: str) -> datetime | None:
        return self._latest_indexed_at

    def has_any_points(self, collection_name: str) -> bool:
        return self._has_any_points


def make_runtime_services(settings: object, qdrant: object | None = None):
    @contextmanager
    def _runtime_services(_settings: object):
        yield type("Runtime", (), {"settings": settings, "qdrant": qdrant or object(), "openai_gateway": object()})()

    return _runtime_services
