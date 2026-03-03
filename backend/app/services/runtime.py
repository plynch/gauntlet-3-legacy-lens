from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from app.core.settings import Settings
from app.services.openai_gateway import OpenAIGateway
from app.services.qdrant_gateway import QdrantGateway
from app.services.tracing import LangfuseTracer


@dataclass(slots=True)
class RuntimeServices:
    settings: Settings
    qdrant: QdrantGateway
    openai_gateway: OpenAIGateway
    tracer: LangfuseTracer


@contextmanager
def runtime_services(settings: Settings) -> Iterator[RuntimeServices]:
    tracer = LangfuseTracer(
        base_url=settings.langfuse_base_url,
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        environment=settings.environment,
    )
    qdrant = QdrantGateway(base_url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    openai_gateway = OpenAIGateway(
        api_key=settings.openai_api_key,
        timeout_seconds=settings.openai_timeout_seconds,
        local_embedding_dimensions=settings.local_embedding_dimensions,
        embedding_max_retries=settings.embedding_max_retries,
        embedding_retry_backoff_seconds=settings.embedding_retry_backoff_seconds,
        tracer=tracer,
    )
    try:
        yield RuntimeServices(settings=settings, qdrant=qdrant, openai_gateway=openai_gateway, tracer=tracer)
    finally:
        qdrant.close()
        openai_gateway.close()
        tracer.close()
