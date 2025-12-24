from uuid import UUID

from pydantic import BaseModel


class BalanceResponse(BaseModel):
    """Ответ баланса."""

    external_user_id: UUID
    balance_tokens: int
