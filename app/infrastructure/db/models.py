from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Enum as PgEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities import (
    BalanceReason,
    GenerationKind,
    GenerationStatus,
    TransactionType,
)
from app.infrastructure.db.base import Base


class UserModel(Base):
    """Модель пользователя."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    external_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        unique=True,
        nullable=False,
    )
    api_key_hash: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    api_key_fingerprint: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        unique=True,
    )
    balance_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    transactions: Mapped[list["BalanceTransactionModel"]] = relationship(
        back_populates="user"
    )
    jobs: Mapped[list["GenerationJobModel"]] = relationship(
        back_populates="user"
    )


class BalanceTransactionModel(Base):
    """Модель транзакции баланса."""

    __tablename__ = "balance_transactions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    type: Mapped[TransactionType] = mapped_column(
        PgEnum(TransactionType, name="transaction_type"),
        nullable=False,
    )
    reason: Mapped[BalanceReason] = mapped_column(
        PgEnum(BalanceReason, name="balance_reason"),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    external_ref: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped[UserModel] = relationship(
        back_populates="transactions"
    )


class GenerationJobModel(Base):
    """Модель задачи генерации."""

    __tablename__ = "generation_jobs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    kind: Mapped[GenerationKind] = mapped_column(
        PgEnum(GenerationKind, name="generation_kind"),
        nullable=False,
    )
    model_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    fal_request_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[GenerationStatus] = mapped_column(
        PgEnum(GenerationStatus, name="generation_status"),
        nullable=False,
    )
    cost_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    input_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    result_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    response_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    cancel_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped[UserModel] = relationship(
        back_populates="jobs"
    )
