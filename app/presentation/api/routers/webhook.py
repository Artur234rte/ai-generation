from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from app.application.use_cases.webhook import WebhookTopupService
from app.infrastructure.security.webhook import verify_webhook_secret
from app.presentation.api.dependencies import get_webhook_service
from app.presentation.schemas.webhook import OkResponse, TopupRequest

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post(
    "/topup",
    response_model=OkResponse,
    dependencies=[Depends(verify_webhook_secret)],
)
async def webhook_topup(
    payload: TopupRequest,
    service: WebhookTopupService = Depends(get_webhook_service),
    x_event_id: str | None = Header(default=None, alias="X-Event-Id"),
) -> OkResponse:
    """Обработать вебхук пополнения."""
    await service.handle_topup(
        payload.external_user_id, payload.amount, x_event_id
    )
    return OkResponse(ok=True)
