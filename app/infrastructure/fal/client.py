from typing import Any, cast

import httpx

from app.application.interfaces.fal_client import FalClient
from app.infrastructure.settings import get_settings


class HttpFalClient(FalClient):
    """HTTP-клиент FAL."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self.settings = get_settings()
        self.client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=2.0,
                read=5.0,
                write=5.0,
                pool=5.0,
            )
        )

    @property
    def headers(self) -> dict[str, str]:
        """Заголовки авторизации."""
        return {"Authorization": f"Key {self.settings.fal_key}"}

    async def submit(
        self,
        model_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Отправить задачу."""
        url = f"https://queue.fal.run/{model_id}"
        resp = await self.client.post(
            url,
            json=payload,
            headers=self.headers,
        )
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())

    async def get_status(
        self,
        status_url: str,
    ) -> dict[str, Any]:
        """Получить статус."""
        resp = await self.client.get(
            status_url,
            headers=self.headers,
        )
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())

    async def get_result(
        self,
        response_url: str,
    ) -> dict[str, Any]:
        """Получить результат."""
        resp = await self.client.get(
            response_url,
            headers=self.headers,
        )
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())

    async def cancel(
        self,
        cancel_url: str,
    ) -> dict[str, Any]:
        """Отменить задачу."""
        resp = await self.client.put(
            cancel_url,
            headers=self.headers,
        )
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())
