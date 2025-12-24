import asyncio
import logging
from typing import Callable
from uuid import UUID

from app.application.use_cases.generations import GenerationService
from app.domain.entities import GenerationStatus
from app.infrastructure.db.base import AsyncSessionLocal
from app.infrastructure.db.repositories import (
    SQLAlchemyBalanceTransactionRepository,
    SQLAlchemyGenerationJobRepository,
    SQLAlchemyUserRepository,
)
from app.infrastructure.fal.client import HttpFalClient
from app.infrastructure.settings import get_settings

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 2.0
TOTAL_TIMEOUT_SECONDS = 15 * 60


async def run_generation_job(
    job_id: UUID,
    fal_client_factory: Callable[[], HttpFalClient] | None = None,
    poll_interval_seconds: float = POLL_INTERVAL_SECONDS,
    total_timeout_seconds: float = TOTAL_TIMEOUT_SECONDS,
) -> None:
    """Запустить и отслеживать генерацию."""
    settings = get_settings()
    client = fal_client_factory() if fal_client_factory else HttpFalClient()

    try:
        async with AsyncSessionLocal() as session:
            users = SQLAlchemyUserRepository(session)
            tx_repo = SQLAlchemyBalanceTransactionRepository(session)
            jobs = SQLAlchemyGenerationJobRepository(session)
            service = GenerationService(
                users, jobs, tx_repo, settings.token_prices
            )

            job = await jobs.get(job_id)
            if not job:
                return
            if job.status != GenerationStatus.QUEUED:
                return

            try:
                response = await client.submit(job.model_id, job.input_json)
                request_id = response.get("request_id") or response.get("id")
                status_url = response.get("status_url") or response.get(
                    "statusUrl"
                )
                result_url = response.get("response_url") or response.get(
                    "responseUrl"
                )
                cancel_url = response.get("cancel_url") or response.get(
                    "cancelUrl"
                )
                if not request_id:
                    raise RuntimeError("fal response missing request id")
                if not status_url:
                    status_url = build_status_url(job.model_id, request_id)
                if not result_url:
                    result_url = build_result_url(job.model_id, request_id)
                if not cancel_url:
                    cancel_url = build_cancel_url(job.model_id, request_id)

                job.fal_request_id = request_id
                job.status_url = status_url
                job.response_url = result_url
                job.cancel_url = cancel_url

                await jobs.update_status(
                    job.id,
                    GenerationStatus.SUBMITTED,
                    fal_request_id=request_id,
                    status_url=status_url,
                    response_url=result_url,
                    cancel_url=cancel_url,
                )
                await session.commit()
            except Exception as exc:
                await session.rollback()
                await service.refund_job(job, error_message=str(exc))
                await session.commit()
                logger.error(
                    "generation_submit_failed",
                    extra={"job_id": str(job.id), "error": str(exc)},
                )
                return

            deadline = asyncio.get_event_loop().time() + total_timeout_seconds
            while asyncio.get_event_loop().time() < deadline:
                await asyncio.sleep(poll_interval_seconds)
                try:
                    status_response = await client.get_status(
                        job.status_url
                        or build_status_url(
                            job.model_id, job.fal_request_id or request_id
                        )
                    )
                    status_value = status_response.get(
                        "status"
                    ) or status_response.get("state")
                    status_enum = (
                        GenerationStatus(status_value)
                        if status_value in GenerationStatus._value2member_map_
                        else GenerationStatus.IN_QUEUE
                    )

                    if status_enum in {
                        GenerationStatus.IN_QUEUE,
                        GenerationStatus.IN_PROGRESS,
                        GenerationStatus.SUBMITTED,
                    }:
                        await jobs.update_status(job.id, status_enum)
                        await session.commit()
                        continue

                    if status_enum == GenerationStatus.COMPLETED:
                        result = await client.get_result(
                            job.response_url
                            or build_result_url(
                                job.model_id, job.fal_request_id or request_id
                            )
                        )
                        await jobs.update_status(
                            job.id,
                            GenerationStatus.COMPLETED,
                            result_json=result,
                        )
                        await session.commit()
                        logger.info(
                            "generation_completed",
                            extra={"job_id": str(job.id)},
                        )
                        return

                    await service.refund_job(
                        job,
                        error_message=status_response.get("error", "failed"),
                    )
                    await session.commit()
                    logger.error(
                        "generation_failed", extra={"job_id": str(job.id)}
                    )
                    return
                except Exception as exc:
                    await session.rollback()
                    await service.refund_job(job, error_message=str(exc))
                    await session.commit()
                    logger.error(
                        "generation_poll_failed",
                        extra={"job_id": str(job.id), "error": str(exc)},
                    )
                    return

            await service.refund_job(
                job, error_message="timeout waiting for fal"
            )
            await session.commit()
            logger.error("generation_timeout", extra={"job_id": str(job.id)})
    finally:
        await client.client.aclose()


def base_model(model_id: str) -> str:
    """Базовый идентификатор модели."""
    parts = model_id.split("/")
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return model_id


def build_status_url(model_id: str, request_id: str) -> str:
    """URL статуса."""
    return (
        f"https://queue.fal.run/{base_model(model_id)}"
        f"/requests/{request_id}/status"
    )


def build_result_url(model_id: str, request_id: str) -> str:
    """URL результата."""
    return (
        f"https://queue.fal.run/{base_model(model_id)}/requests/{request_id}"
    )


def build_cancel_url(model_id: str, request_id: str) -> str:
    """URL отмены."""
    return (
        f"https://queue.fal.run/{base_model(model_id)}"
        f"/requests/{request_id}/cancel"
    )
