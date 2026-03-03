from pydantic import BaseModel, Field


class FeatureDefinition(BaseModel):
    key: str
    title: str
    description: str
    requires_subject: bool = False
    example_subject: str | None = None


class FeatureListResponse(BaseModel):
    features: list[FeatureDefinition]


class FeatureQueryRequest(BaseModel):
    subject: str | None = Field(default=None, max_length=500)
    top_k: int | None = Field(default=None, ge=1, le=20)
