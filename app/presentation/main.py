import logging
import uuid
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.infrastructure.background import BackgroundTaskManager
from app.infrastructure.fal.client import HttpFalClient
from app.infrastructure.logging.config import (
    configure_logging,
    request_id_ctx_var,
)
from app.infrastructure.settings import get_settings
from app.presentation.api.routers import (
    auth,
    balance,
    generations,
    health,
    webhook,
)

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения."""
    configure_logging()

    if not getattr(app.state, "task_manager", None):
        app.state.task_manager = BackgroundTaskManager()

    if not getattr(app.state, "fal_client_factory", None):
        app.state.fal_client_factory = HttpFalClient

    try:
        yield
    finally:
        await app.state.task_manager.shutdown()


app = FastAPI(
    title="AI-image-and-video-generator",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_middleware(
    request: Request,
    call_next: Callable,
):
    """Добавить request_id."""
    request_id = request.headers.get(
        "X-Request-Id",
        str(uuid.uuid4()),
    )
    request_id_ctx_var.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_ctx_var.set("")

    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request,
    exc: Exception,
):
    """Обработчик ошибок."""
    logger.error("unhandled_exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "internal server error"},
    )


app.include_router(auth.router)
app.include_router(health.router)
app.include_router(balance.router)
app.include_router(generations.router)
app.include_router(webhook.router)
