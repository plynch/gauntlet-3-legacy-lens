from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from app.core.settings import Settings
from app.services.openai_gateway import OpenAIGateway
from app.services.qdrant_gateway import QdrantGateway


@dataclass(slots=True)
class RuntimeServices:
    settings: Settings
    qdrant: QdrantGateway
    openai_gateway: OpenAIGateway


@contextmanager
def runtime_services(settings: Settings) -> Iterator[RuntimeServices]:
    qdrant = QdrantGateway(base_url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    openai_gateway = OpenAIGateway(
        api_key=settings.openai_api_key,
        local_embedding_dimensions=settings.local_embedding_dimensions,
    )
    try:
        yield RuntimeServices(settings=settings, qdrant=qdrant, openai_gateway=openai_gateway)
    finally:
        qdrant.close()
        openai_gateway.close()
