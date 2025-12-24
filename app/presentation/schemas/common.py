from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, TypeAdapter

from app.domain.entities import GenerationKind, GenerationStatus


class ImageSize(BaseModel):
    """Размер изображения."""

    width: int
    height: int


class GenerationBaseResponse(BaseModel):
    """Краткий ответ генерации."""

    job_id: UUID = Field(..., alias="job_id")
    status: GenerationStatus
    cost_tokens: int
    created_at: Optional[str] = None


class GenerationDetailResponse(BaseModel):
    """Детали генерации."""

    job_id: UUID
    type: GenerationKind = Field(..., alias="type")
    model_id: str
    status: GenerationStatus
    cost_tokens: int
    fal_request_id: str | None = None
    result: dict | None = None
    error_message: str | None = None


class ListGenerationsResponse(BaseModel):
    """Список генераций."""

    items: list[GenerationDetailResponse]
    limit: int
    offset: int


http_url_adapter = TypeAdapter(HttpUrl)


def validate_data_or_url(value: str) -> str:
    """Проверить data или URL."""
    if value.startswith("data:"):
        return value
    http_url_adapter.validate_python(value)
    return value


def validate_url_list(urls: list[str]) -> list[str]:
    """Проверить список URL."""
    return [validate_data_or_url(v) for v in urls]
