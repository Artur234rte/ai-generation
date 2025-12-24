from fastapi import Header, HTTPException, status

from app.infrastructure.settings import get_settings


async def verify_webhook_secret(
    x_webhook_secret: str = Header(..., alias="X-Webhook-Secret")
) -> None:
    """Проверить секрет вебхука."""
    settings = get_settings()
    if x_webhook_secret != settings.payment_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid webhook secret",
        )
