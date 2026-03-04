from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.settings import Settings
from app.models.health import HealthResponse
from app.services.openai_gateway import describe_openai_mode

router = APIRouter()
settings = Settings()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    openai_status = describe_openai_mode(api_key=settings.openai_api_key)
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        timestamp=datetime.now(tz=timezone.utc),
        qdrant_configured=bool(settings.qdrant_url),
        openai_mode=openai_status.mode,
        degraded_reason=openai_status.degraded_reason,
    )
