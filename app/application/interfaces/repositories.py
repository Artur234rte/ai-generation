from abc import ABC, abstractmethod
from typing import Iterable
from uuid import UUID

from app.domain.entities import (
    BalanceReason,
    BalanceTransaction,
    GenerationJob,
    GenerationStatus,
    User,
)


class UserRepository(ABC):
    @abstractmethod
    async def get_by_external_id(
        self, external_user_id: UUID
    ) -> User | None:
        """Получить по внешнему ID."""
        ...

    @abstractmethod
    async def get_by_api_key_fingerprint(
        self, fingerprint: str
    ) -> User | None:
        """Получить по отпечатку ключа."""
        ...

    @abstractmethod
    async def get_by_id_for_update(
        self, user_id: UUID
    ) -> User | None:
        """Получить по ID с блокировкой."""
        ...

    @abstractmethod
    async def create(
        self,
        external_user_id: UUID,
        api_key_hash: str | None,
        api_key_fingerprint: str | None,
    ) -> User:
        """Создать пользователя."""
        ...

    @abstractmethod
    async def update_api_key(
        self,
        user_id: UUID,
        api_key_hash: str,
        api_key_fingerprint: str,
    ) -> None:
        """Обновить ключ API."""
        ...

    @abstractmethod
    async def adjust_balance(self, user_id: UUID, delta: int) -> None:
        """Изменить баланс."""
        ...


class BalanceTransactionRepository(ABC):
    @abstractmethod
    async def add(self, transaction: BalanceTransaction) -> None:
        """Добавить транзакцию."""
        ...

    @abstractmethod
    async def find_by_external_ref(
        self,
        external_ref: str,
        reason: BalanceReason | None = None,
    ) -> BalanceTransaction | None:
        """Найти по внешней ссылке."""
        ...


class GenerationJobRepository(ABC):
    @abstractmethod
    async def create(self, job: GenerationJob) -> GenerationJob:
        """Создать задачу."""
        ...

    @abstractmethod
    async def get(self, job_id: UUID) -> GenerationJob | None:
        """Получить задачу."""
        ...

    @abstractmethod
    async def list_for_user(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> Iterable[GenerationJob]:
        """Список задач пользователя."""
        ...

    @abstractmethod
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
        ...
