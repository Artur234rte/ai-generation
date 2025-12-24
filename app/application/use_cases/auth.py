import secrets
from uuid import UUID

from app.application.interfaces.repositories import UserRepository
from app.domain.entities import User
from app.infrastructure.security.hashing import (
    api_key_fingerprint,
    hash_api_key,
    verify_api_key,
)


class AuthService:
    """Сервис аутентификации."""

    def __init__(self, users: UserRepository):
        self.users = users

    async def register_or_rotate(
        self,
        external_user_id: UUID,
        rotate: bool = False,
    ) -> tuple[User, str]:
        """Зарегистрировать или обновить ключ."""
        user = await self.users.get_by_external_id(external_user_id)

        plaintext_key = secrets.token_urlsafe(32)
        hashed_key = hash_api_key(plaintext_key)
        fingerprint = api_key_fingerprint(plaintext_key)

        if user is None:
            user = await self.users.create(
                external_user_id=external_user_id,
                api_key_hash=hashed_key,
                api_key_fingerprint=fingerprint,
            )
            return user, plaintext_key

        if not rotate:
            raise UserAlreadyExists()

        await self.users.update_api_key(
            user.id,
            api_key_hash=hashed_key,
            api_key_fingerprint=fingerprint,
        )

        refreshed = await self.users.get_by_external_id(external_user_id)
        assert refreshed is not None
        return refreshed, plaintext_key

    async def authenticate(self, api_key: str) -> User | None:
        """Проверить ключ API."""
        fingerprint = api_key_fingerprint(api_key)
        user = await self.users.get_by_api_key_fingerprint(fingerprint)

        if not user or not user.api_key_hash:
            return None

        if not verify_api_key(api_key, user.api_key_hash):
            return None

        return user


class UserAlreadyExists(Exception):
    """Пользователь уже существует."""
    pass