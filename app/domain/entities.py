from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class TransactionType(str, Enum):
    """Тип транзакции."""

    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class BalanceReason(str, Enum):
    """Причина изменения баланса."""

    TOPUP = "TOPUP"
    GENERATION = "GENERATION"
    REFUND = "REFUND"


class GenerationKind(str, Enum):
    """Тип генерации."""

    TEXT_TO_IMAGE = "TEXT_TO_IMAGE"
    IMAGE_TO_IMAGE = "IMAGE_TO_IMAGE"
    TEXT_TO_VIDEO = "TEXT_TO_VIDEO"
    IMAGE_TO_VIDEO = "IMAGE_TO_VIDEO"


class GenerationStatus(str, Enum):
    """Статус генерации."""

    QUEUED = "QUEUED"
    SUBMITTED = "SUBMITTED"
    IN_QUEUE = "IN_QUEUE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


@dataclass(slots=True)
class User:
    """Пользователь."""

    id: UUID
    external_user_id: UUID
    api_key_hash: str | None
    api_key_fingerprint: str | None
    balance_tokens: int
    created_at: datetime


@dataclass(slots=True)
class BalanceTransaction:
    """Транзакция баланса."""

    id: UUID
    user_id: UUID
    type: TransactionType
    reason: BalanceReason
    amount: int
    external_ref: str | None
    created_at: datetime


@dataclass(slots=True)
class GenerationJob:
    """Задача генерации."""

    id: UUID
    user_id: UUID
    kind: GenerationKind
    model_id: str
    fal_request_id: str | None
    status: GenerationStatus
    cost_tokens: int
    input_json: dict[str, Any]
    result_json: dict[str, Any] | None
    error_message: str | None
    status_url: str | None
    response_url: str | None
    cancel_url: str | None
    created_at: datetime
    updated_at: datetime
