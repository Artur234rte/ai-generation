from uuid import UUID, uuid4

import httpx
import pytest
import sqlalchemy as sa

from app.domain.entities import BalanceReason, GenerationKind, GenerationStatus
from app.infrastructure.background import BackgroundTaskManager
from app.infrastructure.db.base import AsyncSessionLocal
from app.infrastructure.db.models import (
    BalanceTransactionModel,
    GenerationJobModel,
    UserModel,
)
from app.infrastructure.fal.client import HttpFalClient
from app.infrastructure.tasks.generations import run_generation_job


@pytest.mark.asyncio
async def test_create_generation_insufficient_balance_returns_402(
    client, user_external_id
):
    """Генерация без баланса возвращает 402."""
    auth_resp = await client.post(
        "/auth", json={"external_user_id": user_external_id}
    )
    api_key = auth_resp.json()["api_key"]

    resp = await client.post(
        "/generations/images/text-to-image",
        json={"prompt": "test prompt"},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 402


@pytest.mark.asyncio
async def test_create_generation_enqueues_job_and_debits_balance(
    client, user_external_id
):
    """Создание генерации списывает баланс и ставит задачу в очередь."""
    await client.post(
        "/webhook/topup",
        json={"external_user_id": user_external_id, "amount": 50},
        headers={"X-Webhook-Secret": "secret", "X-Event-Id": "evt-gen"},
    )
    auth_resp = await client.post(
        "/auth", json={"external_user_id": user_external_id, "rotate": True}
    )
    api_key = auth_resp.json()["api_key"]

    resp = await client.post(
        "/generations/images/text-to-image",
        json={"prompt": "tree"},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 202
    task_manager: BackgroundTaskManager = client.app.state.task_manager
    assert task_manager.enqueued

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            sa.select(UserModel).where(
                UserModel.external_user_id == UUID(user_external_id)
            )
        )
        db_user = result.scalar_one()
        assert db_user.balance_tokens < 50


@pytest.mark.asyncio
async def test_run_generation_job_sets_fal_request_id(
    client, user_external_id
):
    """Выполнение задачи сохраняет fal_request_id и статус."""
    await client.post(
        "/webhook/topup",
        json={"external_user_id": user_external_id, "amount": 50},
        headers={"X-Webhook-Secret": "secret", "X-Event-Id": "evt-worker"},
    )
    auth_resp = await client.post(
        "/auth", json={"external_user_id": user_external_id, "rotate": True}
    )
    api_key = auth_resp.json()["api_key"]
    create_resp = await client.post(
        "/generations/images/text-to-image",
        json={"prompt": "mountain"},
        headers={"X-API-Key": api_key},
    )
    job_id = create_resp.json()["job_id"]

    class DummyFal:
        async def submit(self, model_id, payload):
            return {"request_id": "fal123"}

        async def get_status(self, status_url):
            return {"status": "COMPLETED"}

        async def get_result(self, response_url):
            return {"ok": True}

        async def cancel(self, cancel_url):
            return {"canceled": True}

        @property
        def client(self):
            class DummyClient:
                async def aclose(self):
                    return None

            return DummyClient()

    await run_generation_job(
        UUID(job_id),
        fal_client_factory=DummyFal,
        poll_interval_seconds=0,
        total_timeout_seconds=1,
    )

    async with AsyncSessionLocal() as session:
        job = await session.get(GenerationJobModel, UUID(job_id))
        assert job.fal_request_id == "fal123"
        assert job.status == GenerationStatus.COMPLETED


@pytest.mark.asyncio
async def test_get_generation_returns_status_and_result_when_completed(
    client, user_external_id
):
    """Получение завершённой генерации возвращает результат."""
    await client.post(
        "/webhook/topup",
        json={"external_user_id": user_external_id, "amount": 50},
        headers={"X-Webhook-Secret": "secret", "X-Event-Id": "evt-completed"},
    )
    auth_resp = await client.post(
        "/auth", json={"external_user_id": user_external_id, "rotate": True}
    )
    api_key = auth_resp.json()["api_key"]

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            sa.select(UserModel).where(
                UserModel.external_user_id == UUID(user_external_id)
            )
        )
        user = user_result.scalar_one()
        job = GenerationJobModel(
            id=uuid4(),
            user_id=user.id,
            kind=GenerationKind.TEXT_TO_IMAGE,
            model_id="fal-ai/wan-25-preview/text-to-image",
            fal_request_id="fal123",
            status=GenerationStatus.COMPLETED,
            cost_tokens=5,
            input_json={"prompt": "done"},
            result_json={
                "images": [
                    {"url": "http://example.com", "content_type": "image/png"}
                ]
            },
            error_message=None,
        )
        session.add(job)
        await session.commit()
        stored_id = str(job.id)

    resp = await client.get(
        f"/generations/{stored_id}", headers={"X-API-Key": api_key}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == GenerationStatus.COMPLETED
    assert data["result"]["images"][0]["url"] == "http://example.com"


@pytest.mark.asyncio
async def test_debit_transaction_recorded_on_creation(
    client, user_external_id
):
    """При создании генерации создаётся debit-транзакция."""
    await client.post(
        "/webhook/topup",
        json={"external_user_id": user_external_id, "amount": 20},
        headers={"X-Webhook-Secret": "secret", "X-Event-Id": "evt-debit"},
    )
    auth_resp = await client.post(
        "/auth", json={"external_user_id": user_external_id, "rotate": True}
    )
    api_key = auth_resp.json()["api_key"]

    resp = await client.post(
        "/generations/images/text-to-image",
        json={"prompt": "record debit"},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 202

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            sa.select(UserModel).where(
                UserModel.external_user_id == UUID(user_external_id)
            )
        )
        user = user_result.scalar_one()
        assert user.balance_tokens == 15
        txns = (
            (
                await session.execute(
                    sa.select(BalanceTransactionModel).where(
                        BalanceTransactionModel.reason
                        == BalanceReason.GENERATION
                    )
                )
            )
            .scalars()
            .all()
        )
        assert any(tx.amount == 5 for tx in txns)


@pytest.mark.asyncio
async def test_run_generation_job_uses_status_urls(client, user_external_id):
    """Задача использует status_url и response_url из ответа FAL."""
    await client.post(
        "/webhook/topup",
        json={"external_user_id": user_external_id, "amount": 50},
        headers={"X-Webhook-Secret": "secret", "X-Event-Id": "evt-url"},
    )
    auth_resp = await client.post(
        "/auth", json={"external_user_id": user_external_id, "rotate": True}
    )
    api_key = auth_resp.json()["api_key"]
    create_resp = await client.post(
        "/generations/images/text-to-image",
        json={"prompt": "network"},
        headers={"X-API-Key": api_key},
    )
    job_id = create_resp.json()["job_id"]

    status_url = (
        "https://queue.fal.run/fal-ai/wan-25-preview/requests/req-123/status"
    )
    result_url = "https://queue.fal.run/fal-ai/wan-25-preview/requests/req-123"
    called_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        called_urls.append(str(request.url))
        if (
            request.method == "POST"
            and str(request.url)
            == "https://queue.fal.run/fal-ai/wan-25-preview/text-to-image"
        ):
            return httpx.Response(
                200,
                json={
                    "request_id": "req-123",
                    "status_url": status_url,
                    "response_url": result_url,
                },
            )
        if request.method == "GET" and str(request.url) == status_url:
            return httpx.Response(200, json={"status": "COMPLETED"})
        if request.method == "GET" and str(request.url) == result_url:
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(405)

    transport = httpx.MockTransport(handler)

    await run_generation_job(
        UUID(job_id),
        poll_interval_seconds=0,
        total_timeout_seconds=1,
        fal_client_factory=lambda: HttpFalClient(
            client=httpx.AsyncClient(transport=transport)
        ),
    )

    assert status_url in called_urls
    assert result_url in called_urls

    async with AsyncSessionLocal() as session:
        job = await session.get(GenerationJobModel, UUID(job_id))
        assert job.status == GenerationStatus.COMPLETED
        assert job.status_url == status_url
