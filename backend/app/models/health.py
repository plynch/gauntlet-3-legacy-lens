from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime
    qdrant_configured: bool
    openai_mode: Literal["openai", "fallback"]
    degraded_reason: str | None = None
