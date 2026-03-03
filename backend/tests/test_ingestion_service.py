from pathlib import Path
from unittest.mock import patch

from app.core.settings import Settings
from app.services.ingestion_service import IngestionService
from app.services.types import SourceChunk, SourceFile


class FakeQdrantGateway:
    def __init__(self, should_skip: bool = False, has_existing_points: bool = False) -> None:
        self.should_skip = should_skip
        self.has_existing_points = has_existing_points
        self.ensure_calls = 0
        self.delete_calls = 0
        self.upsert_calls = 0

    def has_matching_file_hash(self, collection_name: str, source_path: str, file_hash: str) -> bool:
        return self.should_skip

    def ensure_collection(self, collection_name: str, vector_size: int) -> None:
        self.ensure_calls += 1

    def delete_points_for_source_path(self, collection_name: str, source_path: str) -> None:
        self.delete_calls += 1

    def upsert_points(self, collection_name: str, chunks: list[SourceChunk], vectors: list[list[float]]) -> None:
        self.upsert_calls += 1

    def has_points_for_source_path(self, collection_name: str, source_path: str) -> bool:
        return self.has_existing_points


class FakeOpenAIGateway:
    def embed_texts(self, texts: list[str], model: str) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


def make_chunk(source_path: str, file_hash: str) -> SourceChunk:
    return SourceChunk(
        id="123e4567-e89b-12d3-a456-426614174000",
        text="READ CUSTOMER-FILE",
        source_path=source_path,
        file_hash=file_hash,
        line_start=10,
        line_end=14,
        section="READ-CUSTOMER",
    )


def test_ingest_incremental_skips_matching_file_hash(tmp_path) -> None:
    settings = Settings(
        source_directories="corpus",
        ingest_benchmark_log_path=str(tmp_path / "benchmarks" / "ingest_runs.jsonl"),
    )
    qdrant = FakeQdrantGateway(should_skip=True)
    service = IngestionService(settings=settings, qdrant=qdrant, openai_gateway=FakeOpenAIGateway())  # type: ignore[arg-type]

    with patch("app.services.ingestion_service.discover_source_files", return_value=[Path("corpus/a.cbl")]), patch(
        "app.services.ingestion_service.load_source_file",
        return_value=SourceFile(path="corpus/a.cbl", text="DATA", sha1="sha1"),
    ):
        stats = service.ingest(mode="incremental")

    assert stats.files_seen == 1
    assert stats.files_indexed == 0
    assert stats.files_skipped == 1
    assert stats.files_unchanged == 1
    assert stats.files_not_indexable == 0
    assert stats.skipped_paths == ["corpus/a.cbl (unchanged file hash)"]
    assert qdrant.upsert_calls == 0


def test_ingest_full_indexes_chunks_and_creates_collection_once(tmp_path) -> None:
    settings = Settings(
        source_directories="corpus",
        ingest_benchmark_log_path=str(tmp_path / "benchmarks" / "ingest_runs.jsonl"),
    )
    qdrant = FakeQdrantGateway(should_skip=False)
    service = IngestionService(settings=settings, qdrant=qdrant, openai_gateway=FakeOpenAIGateway())  # type: ignore[arg-type]

    with patch(
        "app.services.ingestion_service.discover_source_files",
        return_value=[Path("corpus/a.cbl"), Path("corpus/b.cbl")],
    ), patch(
        "app.services.ingestion_service.load_source_file",
        side_effect=[
            SourceFile(path="corpus/a.cbl", text="A", sha1="sha-a"),
            SourceFile(path="corpus/b.cbl", text="B", sha1="sha-b"),
        ],
    ), patch(
        "app.services.ingestion_service.chunk_cobol_source",
        side_effect=[
            [make_chunk("corpus/a.cbl", "sha-a")],
            [make_chunk("corpus/b.cbl", "sha-b")],
        ],
    ):
        stats = service.ingest(mode="full")

    assert stats.files_seen == 2
    assert stats.files_indexed == 2
    assert stats.files_skipped == 0
    assert stats.files_unchanged == 0
    assert stats.files_not_indexable == 0
    assert stats.chunks_indexed == 2
    assert qdrant.ensure_calls == 1
    assert qdrant.delete_calls == 2
    assert qdrant.upsert_calls == 2


def test_ingest_skips_when_no_chunks_emitted(tmp_path) -> None:
    settings = Settings(
        source_directories="corpus",
        ingest_benchmark_log_path=str(tmp_path / "benchmarks" / "ingest_runs.jsonl"),
    )
    qdrant = FakeQdrantGateway(should_skip=False)
    service = IngestionService(settings=settings, qdrant=qdrant, openai_gateway=FakeOpenAIGateway())  # type: ignore[arg-type]

    with patch("app.services.ingestion_service.discover_source_files", return_value=[Path("corpus/a.cbl")]), patch(
        "app.services.ingestion_service.load_source_file",
        return_value=SourceFile(path="corpus/a.cbl", text="", sha1="sha-a"),
    ), patch("app.services.ingestion_service.chunk_cobol_source", return_value=[]):
        stats = service.ingest(mode="full")

    assert stats.files_seen == 1
    assert stats.files_indexed == 0
    assert stats.files_skipped == 1
    assert stats.files_unchanged == 0
    assert stats.files_not_indexable == 1
    assert stats.skipped_paths == ["corpus/a.cbl (no indexable content)"]
    assert qdrant.ensure_calls == 0
    assert qdrant.delete_calls == 0


def test_ingest_deletes_stale_points_when_no_chunks_emitted(tmp_path) -> None:
    settings = Settings(
        source_directories="corpus",
        ingest_benchmark_log_path=str(tmp_path / "benchmarks" / "ingest_runs.jsonl"),
    )
    qdrant = FakeQdrantGateway(should_skip=False, has_existing_points=True)
    service = IngestionService(settings=settings, qdrant=qdrant, openai_gateway=FakeOpenAIGateway())  # type: ignore[arg-type]

    with patch("app.services.ingestion_service.discover_source_files", return_value=[Path("corpus/a.cbl")]), patch(
        "app.services.ingestion_service.load_source_file",
        return_value=SourceFile(path="corpus/a.cbl", text="", sha1="sha-a"),
    ), patch("app.services.ingestion_service.chunk_cobol_source", return_value=[]):
        stats = service.ingest(mode="full")

    assert stats.files_seen == 1
    assert stats.files_indexed == 0
    assert stats.files_skipped == 1
    assert stats.files_unchanged == 0
    assert stats.files_not_indexable == 1
    assert stats.skipped_paths == ["corpus/a.cbl (no indexable content)"]
    assert qdrant.delete_calls == 1
