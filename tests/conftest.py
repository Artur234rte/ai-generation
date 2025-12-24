import asyncio
import os
from typing import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("FAL_KEY", "test")
os.environ.setdefault("PAYMENT_WEBHOOK_SECRET", "secret")
os.environ.setdefault("TOKEN_PRICES_JSON", '{"text_to_image":5}')

from app.infrastructure.background import BackgroundTaskManager
from app.infrastructure.db.base import AsyncSessionLocal, Base, engine
from app.infrastructure.settings import get_settings
from app.presentation.main import app

get_settings.cache_clear()
settings = get_settings()


def pytest_configure():
    """Инициализация состояния приложения для тестов."""
    app.state.task_manager = BackgroundTaskManager(start_tasks=False)
    app.state.fal_client_factory = None


@pytest.fixture(autouse=True, scope="session")
def setup_db():
    """Создать и удалить схему БД для тестов."""

    async def _create_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _drop_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(_create_schema())
    yield
    asyncio.run(_drop_schema())


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Асинхронная сессия БД."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(session) -> AsyncIterator[AsyncClient]:
    """HTTP-клиент для тестирования API."""
    app.state.task_manager = BackgroundTaskManager(start_tasks=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.app = app
        yield ac


@pytest.fixture
def user_external_id() -> str:
    """Случайный внешний ID пользователя."""
    return str(uuid4())
