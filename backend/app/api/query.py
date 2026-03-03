from typing import Literal

from fastapi import APIRouter, HTTPException

from app.core.settings import Settings
from app.models.ingest import IngestStats
from app.models.query import QueryRequest, QueryResponse
from app.services.ingestion_service import IngestionService
from app.services.query_service import QueryService
from app.services.runtime import runtime_services

router = APIRouter()
settings = Settings()


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
