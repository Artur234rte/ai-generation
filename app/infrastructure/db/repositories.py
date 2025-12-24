from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.repositories import (
    BalanceTransactionRepository,
    GenerationJobRepository,
    UserRepository,
)
from app.domain.entities import (
    BalanceReason,
    BalanceTransaction,
    GenerationJob,
    GenerationStatus,
    User,
)
from app.infrastructure.db.models import (
    BalanceTransactionModel,
    GenerationJobModel,
    UserModel,
)


class SQLAlchemyUserRepository(UserRepository):
    """Репозиторий пользователей."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, model: UserModel) -> User:
        """Преобразовать в доменную модель."""
        return User(
            id=model.id,
            external_user_id=model.external_user_id,
            api_key_hash=model.api_key_hash,
            api_key_fingerprint=model.api_key_fingerprint,
            balance_tokens=model.balance_tokens,
            created_at=model.created_at,
        )

    async def get_by_external_id(
        self,
        external_user_id: UUID,
    ) -> User | None:
        """Получить по внешнему ID."""
        result = await self.session.execute(
            select(UserModel).where(
                UserModel.external_user_id == external_user_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_api_key_fingerprint(
        self,
        fingerprint: str,
    ) -> User | None:
        """Получить по отпечатку ключа."""
        result = await self.session.execute(
            select(UserModel).where(
                UserModel.api_key_fingerprint == fingerprint
            )
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_id_for_update(
        self,
        user_id: UUID,
    ) -> User | None:
        """Получить с блокировкой."""
        result = await self.session.execute(
            select(UserModel)
            .where(UserModel.id == user_id)
            .with_for_update()
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def create(
        self,
        external_user_id: UUID,
        api_key_hash: str | None,
        api_key_fingerprint: str | None,
    ) -> User:
        """Создать пользователя."""
        model = UserModel(
            external_user_id=external_user_id,
            api_key_hash=api_key_hash,
            api_key_fingerprint=api_key_fingerprint,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_domain(model)

    async def update_api_key(
        self,
        user_id: UUID,
        api_key_hash: str,
        api_key_fingerprint: str,
    ) -> None:
        """Обновить ключ API."""
        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(
                api_key_hash=api_key_hash,
                api_key_fingerprint=api_key_fingerprint,
            )
        )

    async def adjust_balance(
        self,
        user_id: UUID,
        delta: int,
    ) -> None:
        """Изменить баланс."""
        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(balance_tokens=UserModel.balance_tokens + delta)
        )


class SQLAlchemyBalanceTransactionRepository(
    BalanceTransactionRepository
):
    """Репозиторий транзакций."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(
        self,
        model: BalanceTransactionModel,
    ) -> BalanceTransaction:
        """Преобразовать в доменную модель."""
        return BalanceTransaction(
            id=model.id,
            user_id=model.user_id,
            type=model.type,
            reason=model.reason,
            amount=model.amount,
            external_ref=model.external_ref,
            created_at=model.created_at,
        )

    async def add(
        self,
        transaction: BalanceTransaction,
    ) -> None:
        """Добавить транзакцию."""
        model = BalanceTransactionModel(
            id=transaction.id,
            user_id=transaction.user_id,
            type=transaction.type,
            reason=transaction.reason,
            amount=transaction.amount,
            external_ref=transaction.external_ref,
            created_at=transaction.created_at,
        )
        self.session.add(model)
        await self.session.flush()

    async def find_by_external_ref(
        self,
        external_ref: str,
        reason: BalanceReason | None = None,
    ) -> BalanceTransaction | None:
        """Найти по внешней ссылке."""
        query = select(BalanceTransactionModel).where(
            BalanceTransactionModel.external_ref == external_ref
        )
        if reason:
            query = query.where(
                BalanceTransactionModel.reason == reason
            )
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None


class SQLAlchemyGenerationJobRepository(
    GenerationJobRepository
):
    """Репозиторий задач генерации."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(
        self,
        model: GenerationJobModel,
    ) -> GenerationJob:
        """Преобразовать в доменную модель."""
        return GenerationJob(
            id=model.id,
            user_id=model.user_id,
            kind=model.kind,
            model_id=model.model_id,
            fal_request_id=model.fal_request_id,
            status=model.status,
            cost_tokens=model.cost_tokens,
            input_json=model.input_json,
            result_json=model.result_json,
            error_message=model.error_message,
            status_url=model.status_url,
            response_url=model.response_url,
            cancel_url=model.cancel_url,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def create(
        self,
        job: GenerationJob,
    ) -> GenerationJob:
        """Создать задачу."""
        model = GenerationJobModel(
            id=job.id,
            user_id=job.user_id,
            kind=job.kind,
            model_id=job.model_id,
            fal_request_id=job.fal_request_id,
            status=job.status,
            cost_tokens=job.cost_tokens,
            input_json=job.input_json,
            result_json=job.result_json,
            error_message=job.error_message,
            status_url=job.status_url,
            response_url=job.response_url,
            cancel_url=job.cancel_url,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_domain(model)

    async def get(
        self,
        job_id: UUID,
    ) -> GenerationJob | None:
        """Получить задачу."""
        result = await self.session.execute(
            select(GenerationJobModel).where(
                GenerationJobModel.id == job_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_for_user(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> Iterable[GenerationJob]:
        """Список задач пользователя."""
        result = await self.session.execute(
            select(GenerationJobModel)
            .where(GenerationJobModel.user_id == user_id)
            .order_by(GenerationJobModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [
            self._to_domain(model)
            for model in result.scalars().all()
        ]

    async def update_status(
        self,
        job_id: UUID,
        status: GenerationStatus,
        fal_request_id: str | None = None,
        result_json: dict | None = None,
        error_message: str | None = None,
        status_url: str | None = None,
        response_url: str | None = None,
        cancel_url: str | None = None,
    ) -> None:
        """Обновить статус."""
        values = {
            "status": status,
            "result_json": result_json,
            "error_message": error_message,
            "updated_at": datetime.now(timezone.utc),
        }

        if fal_request_id is not None:
            values["fal_request_id"] = fal_request_id
        if status_url is not None:
            values["status_url"] = status_url
        if response_url is not None:
            values["response_url"] = response_url
        if cancel_url is not None:
            values["cancel_url"] = cancel_url

        await self.session.execute(
            update(GenerationJobModel)
            .where(GenerationJobModel.id == job_id)
            .values(**values)
        )
