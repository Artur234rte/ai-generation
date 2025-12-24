from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID, uuid4

from app.application.interfaces.repositories import (
    BalanceTransactionRepository,
    GenerationJobRepository,
    UserRepository,
)
from app.domain.entities import (
    BalanceReason,
    BalanceTransaction,
    GenerationJob,
    GenerationKind,
    GenerationStatus,
    TransactionType,
    User,
)


class InsufficientBalance(Exception):
    """Недостаточно средств."""


class GenerationService:
    """Сервис генераций."""

    def __init__(
        self,
        users: UserRepository,
        jobs: GenerationJobRepository,
        transactions: BalanceTransactionRepository,
        token_prices: dict[str, int],
    ):
        self.users = users
        self.jobs = jobs
        self.transactions = transactions
        self.token_prices = token_prices

    def calculate_cost(
        self,
        kind: GenerationKind,
        duration: int | None = None,
    ) -> int:
        """Рассчитать стоимость."""
        if kind == GenerationKind.TEXT_TO_IMAGE:
            return self.token_prices.get("text_to_image", 5)
        if kind == GenerationKind.IMAGE_TO_IMAGE:
            return self.token_prices.get("image_to_image", 6)
        if kind == GenerationKind.TEXT_TO_VIDEO:
            if duration == 10:
                return self.token_prices.get("text_to_video_10s", 55)
            return self.token_prices.get("text_to_video_5s", 30)
        if kind == GenerationKind.IMAGE_TO_VIDEO:
            if duration == 10:
                return self.token_prices.get("image_to_video_10s", 65)
            return self.token_prices.get("image_to_video_5s", 35)
        raise ValueError("Unknown generation kind")

    async def create_job(
        self,
        user: User,
        kind: GenerationKind,
        model_id: str,
        input_payload: dict[str, Any],
        duration: int | None = None,
    ) -> GenerationJob:
        """Создать задачу."""
        cost = self.calculate_cost(kind, duration)
        locked_user = await self.users.get_by_id_for_update(user.id)
        if not locked_user or locked_user.balance_tokens < cost:
            raise InsufficientBalance()

        txn = BalanceTransaction(
            id=uuid4(),
            user_id=locked_user.id,
            type=TransactionType.DEBIT,
            reason=BalanceReason.GENERATION,
            amount=cost,
            external_ref=None,
            created_at=datetime.now(timezone.utc),
        )
        job = GenerationJob(
            id=uuid4(),
            user_id=locked_user.id,
            kind=kind,
            model_id=model_id,
            fal_request_id=None,
            status=GenerationStatus.QUEUED,
            cost_tokens=cost,
            input_json=input_payload,
            result_json=None,
            error_message=None,
            status_url=None,
            response_url=None,
            cancel_url=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await self.transactions.add(txn)
        await self.users.adjust_balance(locked_user.id, -cost)
        await self.jobs.create(job)
        return job

    async def refund_job(
        self,
        job: GenerationJob,
        error_message: str | None = None,
        status: GenerationStatus = GenerationStatus.FAILED,
    ) -> None:
        """Вернуть средства."""
        txn = BalanceTransaction(
            id=uuid4(),
            user_id=job.user_id,
            type=TransactionType.CREDIT,
            reason=BalanceReason.REFUND,
            amount=job.cost_tokens,
            external_ref=str(job.id),
            created_at=datetime.now(timezone.utc),
        )
        await self.transactions.add(txn)
        await self.users.adjust_balance(job.user_id, job.cost_tokens)
        await self.jobs.update_status(
            job.id,
            status,
            error_message=error_message,
        )

    async def list_jobs(
        self,
        user: User,
        limit: int,
        offset: int,
    ) -> Iterable[GenerationJob]:
        """Список задач."""
        return await self.jobs.list_for_user(user.id, limit, offset)

    async def get_job(
        self,
        job_id: UUID,
        user: User,
    ) -> GenerationJob | None:
        """Получить задачу."""
        job = await self.jobs.get(job_id)
        if job and job.user_id == user.id:
            return job
        return None
