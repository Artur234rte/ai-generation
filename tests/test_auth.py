import pytest


@pytest.mark.asyncio
async def test_auth_creates_user_and_returns_key(client, user_external_id):
    """Создание пользователя и повторная регистрация без ротации."""
    response = await client.post(
        "/auth", json={"external_user_id": user_external_id}
    )
    assert response.status_code == 201
    data = response.json()
    assert "api_key" in data
    assert data["external_user_id"] == user_external_id

    response2 = await client.post(
        "/auth", json={"external_user_id": user_external_id}
    )
    assert response2.status_code == 409
