from abc import ABC, abstractmethod
from typing import Any, Mapping


class FalClient(ABC):
    @abstractmethod
    async def submit(
        self,
        model_id: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Отправить задачу."""
        ...

    @abstractmethod
    async def get_status(self, status_url: str) -> dict[str, Any]:
        """Получить статус."""
        ...

    @abstractmethod
    async def get_result(self, response_url: str) -> dict[str, Any]:
        """Получить результат."""
        ...

    @abstractmethod
    async def cancel(self, cancel_url: str) -> dict[str, Any]:
        """Отменить задачу."""
        ...
