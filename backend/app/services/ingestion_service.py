from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from app.core.settings import Settings
from app.models.ingest import IngestStats
from app.services.cobol_chunker import chunk_cobol_source
from app.services.file_discovery import discover_source_files, load_source_file
from app.services.ingest_benchmarks import append_ingest_run
from app.services.openai_gateway import OpenAIGateway
from app.services.qdrant_gateway import QdrantGateway
from app.services.tracing import LangfuseTracer
from app.services.types import SourceChunk


class IngestionService:
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

    def ingest(self, mode: str = "incremental") -> IngestStats:
        with self._ingest_trace(mode=mode) as trace:
            started_at = datetime.now(timezone.utc)
            files = discover_source_files(
                source_directories=self._settings.source_directories,
                source_extensions=self._settings.source_extensions,
            )

            files_seen = len(files)
            if files_seen == 0:
                configured_paths = ", ".join(self._settings.source_directories)
                existing_index_present = self._qdrant.has_any_points(self._settings.qdrant_collection)
                if existing_index_present:
                    raise RuntimeError(
                        "No source files were discovered under configured source directories "
                        f"({configured_paths}). Existing indexed corpus was preserved. "
                        "Run SourceForge sync before indexing."
                    )
                raise RuntimeError(
                    "No source files were discovered under configured source directories "
                    f"({configured_paths}). Run SourceForge sync before indexing."
                )

            files_indexed = 0
            files_skipped = 0
            files_unchanged = 0
            files_not_indexable = 0
            chunks_indexed = 0
            corpus_bytes = 0
            corpus_loc = 0
            skipped_paths: list[str] = []
            collection_ready = False
            indexed_at = started_at.isoformat()

            if mode == "full":
                # Full ingest should represent the current source tree only.
                # Dropping stale vectors prevents old corpora from polluting retrieval.
                self._qdrant.drop_collection_if_exists(self._settings.qdrant_collection)

            for path in files:
                indexed_chunks, file_bytes, file_loc, skip_reason = self._ingest_file(
                    path=path, mode=mode, collection_ready=collection_ready, indexed_at=indexed_at
                )
                corpus_bytes += file_bytes
                corpus_loc += file_loc
                if indexed_chunks == 0:
                    files_skipped += 1
                    if skip_reason == "unchanged":
                        files_unchanged += 1
                        if len(skipped_paths) < 15:
                            skipped_paths.append(f"{path} (unchanged file hash)")
                    elif skip_reason == "not_indexable":
                        files_not_indexable += 1
                        if len(skipped_paths) < 15:
                            skipped_paths.append(f"{path} (no indexable content)")
                    elif skip_reason and len(skipped_paths) < 15:
                        skipped_paths.append(f"{path} ({skip_reason})")
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
                files_unchanged=files_unchanged,
                files_not_indexable=files_not_indexable,
                chunks_indexed=chunks_indexed,
                corpus_bytes=corpus_bytes,
                corpus_loc=corpus_loc,
                skipped_paths=skipped_paths,
            )
            trace.update(
                output={
                    "mode": mode,
                    "files_seen": stats.files_seen,
                    "files_indexed": stats.files_indexed,
                    "files_unchanged": stats.files_unchanged,
                    "files_not_indexable": stats.files_not_indexable,
                    "chunks_indexed": stats.chunks_indexed,
                    "duration_seconds": stats.duration_seconds,
                    "corpus_loc": stats.corpus_loc,
                }
            )
            try:
                append_ingest_run(self._settings.ingest_benchmark_log_path, stats)
            except OSError:
                # Benchmark logging should not block successful indexing.
                pass
            return stats

    def _ingest_file(
        self, path: Path, mode: str, collection_ready: bool, indexed_at: str
    ) -> tuple[int, int, int, Literal["unchanged", "not_indexable"] | None]:
        source = load_source_file(path)
        file_bytes = len(source.text.encode("utf-8", errors="ignore"))
        file_loc = len(source.text.splitlines())
        if mode == "incremental" and self._qdrant.has_matching_file_hash(
            self._settings.qdrant_collection, source.path, source.sha1
        ):
            return 0, file_bytes, file_loc, "unchanged"

        chunks = chunk_cobol_source(
            source=source,
            max_lines=self._settings.chunk_max_lines,
            overlap_lines=self._settings.chunk_overlap_lines,
        )
        if not chunks:
            if self._qdrant.has_points_for_source_path(self._settings.qdrant_collection, source.path):
                self._qdrant.delete_points_for_source_path(self._settings.qdrant_collection, source.path)
            return 0, file_bytes, file_loc, "not_indexable"

        vectors = self._embed_chunks(chunks)
        if vectors:
            if not collection_ready:
                self._qdrant.ensure_collection(self._settings.qdrant_collection, vector_size=len(vectors[0]))
            self._qdrant.delete_points_for_source_path(self._settings.qdrant_collection, source.path)
            self._qdrant.upsert_points(
                self._settings.qdrant_collection,
                chunks=chunks,
                vectors=vectors,
                indexed_at=indexed_at,
            )

        return len(chunks), file_bytes, file_loc, None

    def _embed_chunks(self, chunks: list[SourceChunk]) -> list[list[float]]:
        vectors: list[list[float]] = []
        batch_size = max(1, self._settings.embedding_batch_size)
        for batch in batched(chunks, batch_size):
            texts = [item.text for item in batch]
            vectors.extend(self._embed_texts_with_timeout_fallback(texts))
        return vectors

    def _embed_texts_with_timeout_fallback(self, texts: list[str]) -> list[list[float]]:
        try:
            return self._openai_gateway.embed_texts(texts, model=self._settings.embedding_model)
        except RuntimeError as exc:
            message = str(exc).lower()
            if len(texts) == 1 or "timed out" not in message:
                raise

            midpoint = max(1, len(texts) // 2)
            left_vectors = self._embed_texts_with_timeout_fallback(texts[:midpoint])
            right_vectors = self._embed_texts_with_timeout_fallback(texts[midpoint:])
            return left_vectors + right_vectors

    def _ingest_trace(self, *, mode: str):
        if not self._tracer:
            return _NullTraceContext()
        return self._tracer.span(
            name="ingest.run",
            input={"mode": mode},
            metadata={
                "source_directories": self._settings.source_directories,
                "source_extensions": self._settings.source_extensions,
                "chunk_max_lines": self._settings.chunk_max_lines,
                "chunk_overlap_lines": self._settings.chunk_overlap_lines,
            },
        )


def batched(items: list[SourceChunk], size: int) -> Iterable[list[SourceChunk]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


class _NullTraceContext:
    def __enter__(self):
        return _NullTrace()

    def __exit__(self, exc_type, exc, tb):
        return False


class _NullTrace:
    def update(self, **kwargs: object) -> None:  # pragma: no cover - trivial no-op
        return
