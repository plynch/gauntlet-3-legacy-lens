from typing import Literal

from fastapi import APIRouter, HTTPException

from app.core.settings import Settings
from app.models.corpus import SourceForgeFullIngestResponse, SourceForgeSyncStats
from app.models.features import FeatureListResponse, FeatureQueryRequest
from app.models.ingest import IngestStats
from app.models.query import QueryRequest, QueryResponse
from app.services.feature_catalog import build_feature_question, has_feature, list_features
from app.services.ingest_benchmarks import read_ingest_runs
from app.services.ingestion_service import IngestionService
from app.services.query_service import QueryService
from app.services.runtime import runtime_services
from app.services.sourceforge_corpus import sync_sourceforge_trunk

router = APIRouter()
settings = Settings()


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
            )
            return query_service.answer(question=payload.question, top_k=payload.top_k)
    except Exception as exc:  # pragma: no cover - handled by integration testing
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc


@router.post("/ingest", response_model=IngestStats)
def run_ingest(mode: Literal["full", "incremental"] = "incremental") -> IngestStats:
    try:
        with runtime_services(settings) as services:
            ingestion_service = IngestionService(
                settings=services.settings,
                qdrant=services.qdrant,
                openai_gateway=services.openai_gateway,
            )
            return ingestion_service.ingest(mode=mode)
    except Exception as exc:  # pragma: no cover - handled by integration testing
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc


@router.get("/ingest/runs", response_model=list[IngestStats])
def get_ingest_runs(limit: int | None = None) -> list[IngestStats]:
    requested_limit = limit if limit is not None else settings.ingest_benchmark_read_limit
    capped_limit = max(1, min(requested_limit, 200))
    return read_ingest_runs(settings.ingest_benchmark_log_path, limit=capped_limit)


@router.post("/corpus/sourceforge/sync", response_model=SourceForgeSyncStats)
def sync_sourceforge() -> SourceForgeSyncStats:
    try:
        destination = settings.source_directories[0]
        return sync_sourceforge_trunk(destination, timeout_seconds=settings.sourceforge_sync_timeout_seconds)
    except Exception as exc:  # pragma: no cover - handled by integration testing
        raise HTTPException(status_code=500, detail=f"SourceForge sync failed: {exc}") from exc


@router.post("/corpus/sourceforge/full-ingest", response_model=SourceForgeFullIngestResponse)
def sourceforge_full_ingest() -> SourceForgeFullIngestResponse:
    try:
        destination = settings.source_directories[0]
        sync_stats = sync_sourceforge_trunk(destination, timeout_seconds=settings.sourceforge_sync_timeout_seconds)
        with runtime_services(settings) as services:
            ingestion_service = IngestionService(
                settings=services.settings,
                qdrant=services.qdrant,
                openai_gateway=services.openai_gateway,
            )
            ingest_stats = ingestion_service.ingest(mode="full")
        return SourceForgeFullIngestResponse(sync=sync_stats, ingest=ingest_stats)
    except Exception as exc:  # pragma: no cover - handled by integration testing
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
            )
            question = build_feature_question(feature_key, payload.subject)
            return query_service.answer(question=question, top_k=payload.top_k)
    except Exception as exc:  # pragma: no cover - handled by integration testing
        raise HTTPException(status_code=500, detail=f"Feature query failed: {exc}") from exc
