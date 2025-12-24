from datetime import datetime, timezone
from uuid import uuid4

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


class BalanceService:
    """Сервис баланса."""

    def __init__(
        self,
        users: UserRepository,
        transactions: BalanceTransactionRepository,
    ):
        self.users = users
        self.transactions = transactions

    async def get_balance(self, user: User) -> int:
        """Получить баланс."""
        return user.balance_tokens

    async def credit(
        self,
        user: User,
        amount: int,
        reason: BalanceReason,
        external_ref: str | None = None,
    ) -> None:
        """Начислить токены."""
        txn = BalanceTransaction(
            id=uuid4(),
            user_id=user.id,
            type=TransactionType.CREDIT,
            reason=reason,
            amount=amount,
            external_ref=external_ref,
            created_at=datetime.now(timezone.utc),
        )
        await self.transactions.add(txn)
        await self.users.adjust_balance(user.id, amount)
