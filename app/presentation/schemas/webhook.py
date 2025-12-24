from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class TopupRequest(BaseModel):
    """Запрос пополнения."""

    external_user_id: UUID
    amount: int = Field(..., gt=0)


class OkResponse(BaseModel):
    """OK-ответ."""

    ok: bool
