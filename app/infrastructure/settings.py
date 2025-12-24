import json
import os
from functools import lru_cache
from typing import Any

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
)

DEFAULT_TOKEN_PRICES = {
    "text_to_image": 5,
    "image_to_image": 6,
    "text_to_video_5s": 30,
    "text_to_video_10s": 55,
    "image_to_video_5s": 35,
    "image_to_video_10s": 65,
}


class Settings(BaseModel):
    """Настройки приложения."""

    database_url: str = Field(alias="DATABASE_URL")
    fal_key: str = Field(alias="FAL_KEY")
    payment_webhook_secret: str = Field(alias="PAYMENT_WEBHOOK_SECRET")
    token_prices_json: str = Field(alias="TOKEN_PRICES_JSON")

    @field_validator(
        "database_url",
        "fal_key",
        "payment_webhook_secret",
        "token_prices_json",
        mode="before",
    )
    @classmethod
    def _ensure_present(cls, value: Any, info: ValidationInfo):
        """Проверить наличие значения."""
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"{info.field_name} must be set")
        return value

    @classmethod
    def from_env(cls) -> "Settings":
        """Загрузить из окружения."""
        raw = {
            "DATABASE_URL": os.getenv("DATABASE_URL"),
            "FAL_KEY": os.getenv("FAL_KEY"),
            "PAYMENT_WEBHOOK_SECRET": os.getenv("PAYMENT_WEBHOOK_SECRET"),
            "TOKEN_PRICES_JSON": os.getenv("TOKEN_PRICES_JSON"),
        }
        cleaned = {k: v for k, v in raw.items() if v is not None}
        return cls.model_validate(cleaned)

    @property
    def token_prices(self) -> dict[str, int]:
        """Цены токенов."""
        try:
            data: dict[str, Any] = json.loads(self.token_prices_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError("TOKEN_PRICES_JSON must be valid JSON") from exc

        if not isinstance(data, dict):
            raise RuntimeError("TOKEN_PRICES_JSON must be a JSON object")

        return {
            **DEFAULT_TOKEN_PRICES,
            **{k: int(v) for k, v in data.items()},
        }


@lru_cache()
def get_settings() -> Settings:
    """Получить настройки."""
    try:
        return Settings.from_env()
    except ValidationError as exc:
        missing = ", ".join(str(err["loc"][0]) for err in exc.errors())
        raise RuntimeError(
            f"Missing required environment variables: {missing}"
        ) from exc
