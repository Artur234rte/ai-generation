from uuid import uuid4

import pytest

WEBHOOK_SECRET = "secret"


@pytest.mark.asyncio
async def test_webhook_topup_increases_balance_and_is_idempotent_with_event_id(
    client,
):
    """Пополнение увеличивает баланс и идемпотентно по event_id."""
    external_user_id = str(uuid4())
    amount = 100
    event_id = str(uuid4())
    headers = {"X-Webhook-Secret": WEBHOOK_SECRET, "X-Event-Id": event_id}
    response = await client.post(
        "/webhook/topup",
        json={"external_user_id": external_user_id, "amount": amount},
        headers=headers,
    )
    assert response.status_code == 200

    auth_resp = await client.post(
        "/auth", json={"external_user_id": external_user_id, "rotate": True}
    )
    assert auth_resp.status_code == 201 or auth_resp.status_code == 200
    api_key = auth_resp.json()["api_key"]

    balance_resp = await client.get("/balance", headers={"X-API-Key": api_key})
    assert balance_resp.status_code == 200
    assert balance_resp.json()["balance_tokens"] == amount

    response2 = await client.post(
        "/webhook/topup",
        json={"external_user_id": external_user_id, "amount": amount},
        headers=headers,
    )
    assert response2.status_code == 200

    balance_resp2 = await client.get(
        "/balance", headers={"X-API-Key": api_key}
    )
    assert balance_resp2.json()["balance_tokens"] == amount


@pytest.mark.asyncio
async def test_webhook_topup_allows_multiple_event_ids(client):
    """Разные event_id приводят к нескольким пополнениям."""
    external_user_id = str(uuid4())
    amount = 50
    headers1 = {"X-Webhook-Secret": WEBHOOK_SECRET, "X-Event-Id": str(uuid4())}
    headers2 = {"X-Webhook-Secret": WEBHOOK_SECRET, "X-Event-Id": str(uuid4())}
    await client.post(
        "/webhook/topup",
        json={"external_user_id": external_user_id, "amount": amount},
        headers=headers1,
    )
    await client.post(
        "/webhook/topup",
        json={"external_user_id": external_user_id, "amount": amount},
        headers=headers2,
    )

    auth_resp = await client.post(
        "/auth", json={"external_user_id": external_user_id, "rotate": True}
    )
    api_key = auth_resp.json()["api_key"]
    balance_resp = await client.get("/balance", headers={"X-API-Key": api_key})
    assert balance_resp.json()["balance_tokens"] == amount * 2


@pytest.mark.asyncio
async def test_webhook_topup_without_event_id_always_credits(client):
    """Пополнение без event_id всегда увеличивает баланс."""
    external_user_id = str(uuid4())
    amount = 25
    headers = {"X-Webhook-Secret": WEBHOOK_SECRET}
    await client.post(
        "/webhook/topup",
        json={"external_user_id": external_user_id, "amount": amount},
        headers=headers,
    )
    await client.post(
        "/webhook/topup",
        json={"external_user_id": external_user_id, "amount": amount},
        headers=headers,
    )

    auth_resp = await client.post(
        "/auth", json={"external_user_id": external_user_id, "rotate": True}
    )
    api_key = auth_resp.json()["api_key"]
    balance_resp = await client.get("/balance", headers={"X-API-Key": api_key})
    assert balance_resp.json()["balance_tokens"] == amount * 2
