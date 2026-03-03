from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from app.core.settings import Settings
from app.models.ingest import IngestStats
from app.services.cobol_chunker import chunk_cobol_source
from app.services.file_discovery import discover_source_files, load_source_file
from app.services.ingest_benchmarks import append_ingest_run
from app.services.openai_gateway import OpenAIGateway
from app.services.qdrant_gateway import QdrantGateway
from app.services.types import SourceChunk


class IngestionService:
    def __init__(self, settings: Settings, qdrant: QdrantGateway, openai_gateway: OpenAIGateway) -> None:
        self._settings = settings
        self._qdrant = qdrant
        self._openai_gateway = openai_gateway

    def ingest(self, mode: str = "incremental") -> IngestStats:
        started_at = datetime.now(timezone.utc)
        files = discover_source_files(
            source_directories=self._settings.source_directories,
            source_extensions=self._settings.source_extensions,
        )

        files_seen = len(files)
        files_indexed = 0
        files_skipped = 0
        chunks_indexed = 0
        corpus_bytes = 0
        corpus_loc = 0
        collection_ready = False

        for path in files:
            indexed_chunks, file_bytes, file_loc = self._ingest_file(
                path=path, mode=mode, collection_ready=collection_ready
            )
            corpus_bytes += file_bytes
            corpus_loc += file_loc
            if indexed_chunks == 0:
                files_skipped += 1
                continue

            files_indexed += 1
            chunks_indexed += indexed_chunks
            collection_ready = True

        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()
        stats = IngestStats(
            mode=mode,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            files_seen=files_seen,
            files_indexed=files_indexed,
            files_skipped=files_skipped,
            chunks_indexed=chunks_indexed,
            corpus_bytes=corpus_bytes,
            corpus_loc=corpus_loc,
        )
        try:
            append_ingest_run(self._settings.ingest_benchmark_log_path, stats)
        except OSError:
            # Benchmark logging should not block successful indexing.
            pass
        return stats

    def _ingest_file(self, path: Path, mode: str, collection_ready: bool) -> tuple[int, int, int]:
        source = load_source_file(path)
        file_bytes = len(source.text.encode("utf-8", errors="ignore"))
        file_loc = len(source.text.splitlines())
        if mode == "incremental" and self._qdrant.has_matching_file_hash(
            self._settings.qdrant_collection, source.path, source.sha1
        ):
            return 0, file_bytes, file_loc

        chunks = chunk_cobol_source(
            source=source,
            max_lines=self._settings.chunk_max_lines,
            overlap_lines=self._settings.chunk_overlap_lines,
        )
        if not chunks:
            if self._qdrant.has_points_for_source_path(self._settings.qdrant_collection, source.path):
                self._qdrant.delete_points_for_source_path(self._settings.qdrant_collection, source.path)
            return 0, file_bytes, file_loc

        vectors = self._embed_chunks(chunks)
        if vectors:
            if not collection_ready:
                self._qdrant.ensure_collection(self._settings.qdrant_collection, vector_size=len(vectors[0]))
            self._qdrant.delete_points_for_source_path(self._settings.qdrant_collection, source.path)
            self._qdrant.upsert_points(self._settings.qdrant_collection, chunks=chunks, vectors=vectors)

        return len(chunks), file_bytes, file_loc

    def _embed_chunks(self, chunks: list[SourceChunk]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in batched(chunks, 64):
            texts = [item.text for item in batch]
            vectors.extend(self._openai_gateway.embed_texts(texts, model=self._settings.embedding_model))
        return vectors


def batched(items: list[SourceChunk], size: int) -> Iterable[list[SourceChunk]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]
