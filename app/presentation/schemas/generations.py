from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.presentation.schemas.common import ImageSize, validate_data_or_url


class TextToImageRequest(BaseModel):
    """Запрос текст→изображение."""

    prompt: str = Field(..., max_length=2000)
    negative_prompt: Optional[str] = Field(None, max_length=2000)
    num_images: int = Field(1, ge=1, le=4)
    image_size: ImageSize | str | None = None
    enable_prompt_expansion: bool | None = None
    seed: int | None = None
    enable_safety_checker: bool | None = None


class ImageToImageRequest(BaseModel):
    """Запрос изображение→изображение."""

    prompt: str = Field(..., max_length=2000)
    image_urls: list[str]
    negative_prompt: Optional[str] = Field(None, max_length=2000)
    image_size: ImageSize | str | None = None
    num_images: int = Field(1, ge=1, le=4)
    seed: int | None = None
    enable_safety_checker: bool | None = None

    @field_validator("image_urls", mode="before")
    @classmethod
    def validate_urls(cls, value: list[str]) -> list[str]:
        """Проверить URL изображений."""
        if not isinstance(value, list) or not (1 <= len(value) <= 2):
            raise ValueError("image_urls must contain 1-2 items")
        return [validate_data_or_url(v) for v in value]


class TextToVideoRequest(BaseModel):
    """Запрос текст→видео."""

    prompt: str = Field(..., max_length=800)
    audio_url: Optional[str] = None
    aspect_ratio: Optional[Literal["16:9", "9:16", "1:1"]] = None
    resolution: Optional[Literal["480p", "720p", "1080p"]] = None
    duration: int = Field(5)
    negative_prompt: Optional[str] = Field(None, max_length=800)
    enable_prompt_expansion: bool | None = None
    seed: int | None = None
    enable_safety_checker: bool | None = None

    @field_validator("audio_url")
    @classmethod
    def validate_audio(cls, value: str | None) -> str | None:
        """Проверить URL аудио."""
        if value is None:
            return value
        return validate_data_or_url(value)

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, value: int) -> int:
        """Проверить длительность."""
        if value not in (5, 10):
            raise ValueError("duration must be 5 or 10")
        return value


class ImageToVideoRequest(BaseModel):
    """Запрос изображение→видео."""

    prompt: str = Field(..., max_length=800)
    image_url: str
    audio_url: Optional[str] = None
    resolution: Optional[Literal["480p", "720p", "1080p"]] = None
    duration: int = Field(5)
    negative_prompt: Optional[str] = Field(None, max_length=800)
    enable_prompt_expansion: bool | None = None
    seed: int | None = None
    enable_safety_checker: bool | None = None

    @field_validator("image_url")
    @classmethod
    def validate_image(cls, value: str) -> str:
        """Проверить URL изображения."""
        return validate_data_or_url(value)

    @field_validator("audio_url")
    @classmethod
    def validate_audio(cls, value: str | None) -> str | None:
        """Проверить URL аудио."""
        if value is None:
            return value
        return validate_data_or_url(value)

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, value: int) -> int:
        """Проверить длительность."""
        if value not in (5, 10):
            raise ValueError("duration must be 5 or 10")
        return value
