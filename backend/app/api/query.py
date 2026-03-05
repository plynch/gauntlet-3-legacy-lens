from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException

from app.core.settings import Settings
from app.models.corpus import SourceForgeFullIngestResponse, SourceForgeSyncStats
from app.models.features import FeatureListResponse, FeatureQueryRequest
from app.models.ingest import IngestStats, IngestStatus
from app.models.query import QueryRequest, QueryResponse
from app.services.feature_catalog import build_feature_question, has_feature, list_features
from app.services.ingest_benchmarks import read_ingest_runs
from app.services.ingestion_service import IngestionService
from app.services.ingest_status_store import ingest_status_store
from app.services.query_service import QueryService
from app.services.runtime import runtime_services
from app.services.sourceforge_corpus import sync_sourceforge_trunk

router = APIRouter()
settings = Settings()
AUSTIN_TZ = ZoneInfo("America/Chicago")


@router.get("/features", response_model=FeatureListResponse)
def get_features() -> FeatureListResponse:
    return FeatureListResponse(features=list_features())


@router.post("/query", response_model=QueryResponse)
def run_query(payload: QueryRequest) -> QueryResponse:
    try:
        with runtime_services(settings) as services:
            query_service = QueryService(
                settings=services.settings,
                qdrant=services.qdrant,
                openai_gateway=services.openai_gateway,
                tracer=getattr(services, "tracer", None),
            )
            return query_service.answer(question=payload.question, top_k=payload.top_k)
    except Exception as exc:  # pragma: no cover - handled by integration testing
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc


@router.post("/ingest", response_model=IngestStats)
def run_ingest(mode: Literal["full", "incremental"] = "incremental") -> IngestStats:
    started_label = _format_austin_timestamp(datetime.now(AUSTIN_TZ))
    if not ingest_status_store.try_begin(mode=mode, phase="indexing", summary=f"Began {mode} ingest at {started_label}."):
        raise HTTPException(status_code=409, detail=_ingest_busy_detail())
    try:
        with runtime_services(settings) as services:
            ingestion_service = IngestionService(
                settings=services.settings,
                qdrant=services.qdrant,
                openai_gateway=services.openai_gateway,
                tracer=getattr(services, "tracer", None),
            )
            stats = ingestion_service.ingest(mode=mode)
        ingest_status_store.mark_completed(
            stats,
            summary=f"Began {mode} ingest at {started_label}. Ingest completed at {_format_austin_timestamp(stats.completed_at)}.",
        )
        return stats
    except Exception as exc:  # pragma: no cover - handled by integration testing
        ingest_status_store.mark_failed(error=f"Ingestion failed: {exc}", stage="indexing")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc


@router.get("/ingest/runs", response_model=list[IngestStats])
def get_ingest_runs(limit: int | None = None) -> list[IngestStats]:
    requested_limit = limit if limit is not None else settings.ingest_benchmark_read_limit
    capped_limit = max(1, min(requested_limit, 200))
    return read_ingest_runs(settings.ingest_benchmark_log_path, limit=capped_limit)


@router.get("/ingest/status", response_model=IngestStatus)
def get_ingest_status() -> IngestStatus:
    status = ingest_status_store.snapshot(benchmark_log_path=settings.ingest_benchmark_log_path)
    if status.active or status.last_indexed_at is not None:
        return status

    # Fallback for deployments where local benchmark logs are ephemeral:
    # recover index presence and latest indexed timestamp directly from Qdrant.
    try:
        with runtime_services(settings) as services:
            latest_indexed_at = services.qdrant.get_latest_indexed_at(settings.qdrant_collection)
            if latest_indexed_at is not None:
                ingest_status_store.mark_indexed_data_detected(last_indexed_at=latest_indexed_at)
            elif services.qdrant.has_any_points(settings.qdrant_collection):
                ingest_status_store.mark_indexed_data_detected()
            status = ingest_status_store.snapshot(benchmark_log_path=settings.ingest_benchmark_log_path)
    except Exception:
        # Keep status endpoint resilient even if Qdrant is transiently unavailable.
        pass

    return status


@router.post("/corpus/sourceforge/sync", response_model=SourceForgeSyncStats)
def sync_sourceforge() -> SourceForgeSyncStats:
    sync_started_label = _format_austin_timestamp(datetime.now(AUSTIN_TZ))
    if not ingest_status_store.try_begin(
        mode="full",
        phase="syncing",
        summary=f"Began SourceForge sync at {sync_started_label}.",
    ):
        raise HTTPException(status_code=409, detail=_ingest_busy_detail())
    try:
        destination = settings.source_directories[0]
        sync_stats = sync_sourceforge_trunk(destination, timeout_seconds=settings.sourceforge_sync_timeout_seconds)
        sync_completed_label = _format_austin_timestamp(sync_stats.synced_at)
        ingest_status_store.mark_sync_only_completed(
            sync_stats,
            summary=(
                f"Began SourceForge sync at {sync_started_label}. "
                f"Finished SourceForge sync ({sync_stats.files_synced} files, {sync_stats.corpus_loc} LOC) at {sync_completed_label}."
            ),
        )
        return sync_stats
    except Exception as exc:  # pragma: no cover - handled by integration testing
        ingest_status_store.mark_failed(
            error=f"SourceForge sync failed: {exc}",
            stage="sync",
            summary=f"Began SourceForge sync at {sync_started_label}. SourceForge sync failed before completion.",
        )
        raise HTTPException(status_code=500, detail=f"SourceForge sync failed: {exc}") from exc


@router.post("/corpus/sourceforge/full-ingest", response_model=SourceForgeFullIngestResponse)
def sourceforge_full_ingest() -> SourceForgeFullIngestResponse:
    sync_started_label = _format_austin_timestamp(datetime.now(AUSTIN_TZ))
    if not ingest_status_store.try_begin(
        mode="full",
        phase="syncing",
        summary=f"Began SourceForge sync at {sync_started_label}.",
    ):
        raise HTTPException(status_code=409, detail=_ingest_busy_detail())
    sync_completed_label: str | None = None
    try:
        destination = settings.source_directories[0]
        sync_stats = sync_sourceforge_trunk(destination, timeout_seconds=settings.sourceforge_sync_timeout_seconds)
        sync_completed_label = _format_austin_timestamp(sync_stats.synced_at)
        ingest_status_store.mark_sync_completed(
            sync_stats,
            summary=(
                f"Began SourceForge sync at {sync_started_label}. "
                f"Finished SourceForge sync ({sync_stats.files_synced} files, {sync_stats.corpus_loc} LOC) at {sync_completed_label}. "
                "Starting full indexing."
            ),
        )
        ingest_status_store.mark_indexing_started()
        with runtime_services(settings) as services:
            ingestion_service = IngestionService(
                settings=services.settings,
                qdrant=services.qdrant,
                openai_gateway=services.openai_gateway,
                tracer=getattr(services, "tracer", None),
            )
            ingest_stats = ingestion_service.ingest(mode="full")
        ingest_status_store.mark_completed(
            ingest_stats,
            summary=(
                f"Began SourceForge sync at {sync_started_label}. "
                f"Finished SourceForge sync ({sync_stats.files_synced} files, {sync_stats.corpus_loc} LOC) at {sync_completed_label}. "
                f"Full indexing completed at {_format_austin_timestamp(ingest_stats.completed_at)}."
            ),
        )
        return SourceForgeFullIngestResponse(sync=sync_stats, ingest=ingest_stats)
    except Exception as exc:  # pragma: no cover - handled by integration testing
        if sync_completed_label is None:
            ingest_status_store.mark_failed(
                error=f"SourceForge full ingest failed: {exc}",
                stage="sync",
                summary=f"Began SourceForge sync at {sync_started_label}. SourceForge sync failed before completion.",
            )
        else:
            ingest_status_store.mark_failed(
                error=f"SourceForge full ingest failed: {exc}",
                stage="indexing",
                summary=(
                    f"Began SourceForge sync at {sync_started_label}. "
                    f"Finished SourceForge sync at {sync_completed_label}. Full indexing failed before completion."
                ),
            )
        raise HTTPException(status_code=500, detail=f"SourceForge full ingest failed: {exc}") from exc


@router.post("/features/{feature_key}/query", response_model=QueryResponse)
def run_feature_query(feature_key: str, payload: FeatureQueryRequest) -> QueryResponse:
    if not has_feature(feature_key):
        raise HTTPException(status_code=404, detail=f"Unknown feature: {feature_key}")

    try:
        with runtime_services(settings) as services:
            query_service = QueryService(
                settings=services.settings,
                qdrant=services.qdrant,
                openai_gateway=services.openai_gateway,
                tracer=getattr(services, "tracer", None),
            )
            question = build_feature_question(feature_key, payload.subject)
            return query_service.answer(question=question, top_k=payload.top_k)
    except Exception as exc:  # pragma: no cover - handled by integration testing
        raise HTTPException(status_code=500, detail=f"Feature query failed: {exc}") from exc


def _ingest_busy_detail() -> str:
    status = ingest_status_store.snapshot(benchmark_log_path=settings.ingest_benchmark_log_path)
    phase = status.phase.replace("_", " ")
    mode = status.mode or "unknown"
    return f"Another ingest operation is already in progress (mode={mode}, phase={phase})."


def _format_austin_timestamp(value: datetime) -> str:
    return value.astimezone(AUSTIN_TZ).strftime("%-m/%-d/%Y, %-I:%M:%S %p %Z")
