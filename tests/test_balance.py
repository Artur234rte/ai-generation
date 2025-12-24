import pytest


@pytest.mark.asyncio
async def test_balance_requires_auth(client):
    """Доступ к балансу требует аутентификации."""
    response = await client.get("/balance")
    assert response.status_code == 401
