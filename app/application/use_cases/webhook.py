from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.application.interfaces.repositories import (
    BalanceTransactionRepository,
    UserRepository,
)
from app.domain.entities import (
    BalanceReason,
    BalanceTransaction,
    TransactionType,
    User,
)


class WebhookTopupService:
    """Сервис пополнений."""

    def __init__(
        self,
        users: UserRepository,
        transactions: BalanceTransactionRepository,
    ):
        self.users = users
        self.transactions = transactions

    async def handle_topup(
        self,
        external_user_id: UUID,
        amount: int,
        external_ref: str | None,
    ) -> User:
        """Обработать пополнение."""
        user = await self.users.get_by_external_id(external_user_id)
        if user is None:
            user = await self.users.create(
                external_user_id,
                api_key_hash=None,
                api_key_fingerprint=None,
            )

        locked_user = await self.users.get_by_id_for_update(user.id)
        if locked_user is None:
            raise RuntimeError("Failed to lock user for topup")

        if external_ref:
            existing = await self.transactions.find_by_external_ref(
                external_ref,
                BalanceReason.TOPUP,
            )
            if existing:
                return locked_user

        txn = BalanceTransaction(
            id=uuid4(),
            user_id=locked_user.id,
            type=TransactionType.CREDIT,
            reason=BalanceReason.TOPUP,
            amount=amount,
            external_ref=external_ref,
            created_at=datetime.now(timezone.utc),
        )
        await self.transactions.add(txn)
        await self.users.adjust_balance(locked_user.id, amount)

        refreshed = await self.users.get_by_external_id(external_user_id)
        return refreshed or locked_user
