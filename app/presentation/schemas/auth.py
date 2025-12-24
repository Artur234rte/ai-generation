from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    """Запрос аутентификации."""

    external_user_id: UUID
    rotate: bool = Field(default=False)


class AuthResponse(BaseModel):
    """Ответ аутентификации."""

    external_user_id: UUID
    api_key: str
