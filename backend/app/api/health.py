from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.settings import Settings
from app.models.health import HealthResponse

router = APIRouter()
settings = Settings()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        timestamp=datetime.now(tz=timezone.utc),
        qdrant_configured=bool(settings.qdrant_url),
    )
