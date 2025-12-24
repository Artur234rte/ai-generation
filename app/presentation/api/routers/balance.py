from fastapi import APIRouter, Depends

from app.application.use_cases.balance import BalanceService
from app.domain.entities import User
from app.presentation.api.dependencies import (
    get_balance_service,
    get_current_user,
)
from app.presentation.schemas.balance import BalanceResponse

router = APIRouter(prefix="/balance", tags=["balance"])


@router.get("", response_model=BalanceResponse)
async def get_balance(
    current_user: User = Depends(get_current_user),
    balance_service: BalanceService = Depends(get_balance_service),
) -> BalanceResponse:
    """Получить баланс."""
    balance = await balance_service.get_balance(current_user)
    return BalanceResponse(
        external_user_id=current_user.external_user_id, balance_tokens=balance
    )
