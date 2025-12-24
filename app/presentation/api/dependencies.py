from fastapi import Depends, Header, HTTPException, status

from app.application.use_cases.auth import AuthService
from app.application.use_cases.balance import BalanceService
from app.application.use_cases.generations import GenerationService
from app.application.use_cases.webhook import WebhookTopupService
from app.domain.entities import User
from app.infrastructure.db.base import get_session
from app.infrastructure.db.repositories import (
    SQLAlchemyBalanceTransactionRepository,
    SQLAlchemyGenerationJobRepository,
    SQLAlchemyUserRepository,
)
from app.infrastructure.settings import get_settings


async def get_user_repository(session=Depends(get_session)):
    """Репозиторий пользователей."""
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(session, AsyncSession)
    return SQLAlchemyUserRepository(session)


async def get_transaction_repository(session=Depends(get_session)):
    """Репозиторий транзакций."""
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(session, AsyncSession)
    return SQLAlchemyBalanceTransactionRepository(session)


async def get_job_repository(session=Depends(get_session)):
    """Репозиторий задач."""
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(session, AsyncSession)
    return SQLAlchemyGenerationJobRepository(session)


async def get_auth_service(
    users=Depends(get_user_repository),
) -> AuthService:
    """Сервис аутентификации."""
    return AuthService(users)


async def get_balance_service(
    users=Depends(get_user_repository),
    transactions=Depends(get_transaction_repository),
) -> BalanceService:
    """Сервис баланса."""
    return BalanceService(users, transactions)


async def get_generation_service(
    users=Depends(get_user_repository),
    jobs=Depends(get_job_repository),
    transactions=Depends(get_transaction_repository),
) -> GenerationService:
    """Сервис генераций."""
    settings = get_settings()
    return GenerationService(
        users,
        jobs,
        transactions,
        settings.token_prices,
    )


async def get_webhook_service(
    users=Depends(get_user_repository),
    transactions=Depends(get_transaction_repository),
) -> WebhookTopupService:
    """Сервис вебхуков."""
    return WebhookTopupService(users, transactions)


async def get_current_user(
    api_key: str | None = Header(None, alias="X-API-Key"),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Получить текущего пользователя."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing api key",
        )

    user = await auth_service.authenticate(api_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid api key",
        )

    return user
