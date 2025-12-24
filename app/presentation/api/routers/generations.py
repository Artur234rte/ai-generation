from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.generations import (
    GenerationService,
    InsufficientBalance,
)
from app.domain.entities import GenerationKind, GenerationStatus, User
from app.infrastructure.background import maybe_run_background
from app.infrastructure.db.base import get_session
from app.infrastructure.fal.client import HttpFalClient
from app.infrastructure.tasks.generations import (
    build_cancel_url,
    run_generation_job,
)
from app.presentation.api.dependencies import (
    get_current_user,
    get_generation_service,
)
from app.presentation.schemas.common import (
    GenerationBaseResponse,
    GenerationDetailResponse,
    ListGenerationsResponse,
)
from app.presentation.schemas.generations import (
    ImageToImageRequest,
    ImageToVideoRequest,
    TextToImageRequest,
    TextToVideoRequest,
)

router = APIRouter(prefix="/generations", tags=["generations"])


def job_response(job) -> GenerationBaseResponse:
    """Краткий ответ по задаче."""
    return GenerationBaseResponse(
        job_id=job.id,
        status=job.status,
        cost_tokens=job.cost_tokens,
        created_at=job.created_at.isoformat(),
    )


def detail_response(job) -> GenerationDetailResponse:
    """Детальный ответ по задаче."""
    return GenerationDetailResponse(
        job_id=job.id,
        type=job.kind,
        model_id=job.model_id,
        status=job.status,
        cost_tokens=job.cost_tokens,
        fal_request_id=job.fal_request_id,
        result=job.result_json,
        error_message=job.error_message,
    )


@router.post(
    "/images/text-to-image",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=GenerationBaseResponse,
)
async def create_text_to_image(
    payload: TextToImageRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service),
) -> GenerationBaseResponse:
    """Текст в изображение."""
    try:
        job = await service.create_job(
            current_user,
            GenerationKind.TEXT_TO_IMAGE,
            "fal-ai/wan-25-preview/text-to-image",
            payload.model_dump(exclude_none=True),
        )
    except InsufficientBalance:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="insufficient balance",
        )
    await session.commit()
    maybe_run_background(
        request.app.state.task_manager,
        lambda: run_generation_job(
            job.id, request.app.state.fal_client_factory
        ),
    )
    return job_response(job)


@router.post(
    "/images/image-to-image",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=GenerationBaseResponse,
)
async def create_image_to_image(
    payload: ImageToImageRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service),
) -> GenerationBaseResponse:
    """Изображение в изображение."""
    try:
        job = await service.create_job(
            current_user,
            GenerationKind.IMAGE_TO_IMAGE,
            "fal-ai/wan-25-preview/image-to-image",
            payload.model_dump(exclude_none=True),
        )
    except InsufficientBalance:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="insufficient balance",
        )
    await session.commit()
    maybe_run_background(
        request.app.state.task_manager,
        lambda: run_generation_job(
            job.id, request.app.state.fal_client_factory
        ),
    )
    return job_response(job)


@router.post(
    "/videos/text-to-video",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=GenerationBaseResponse,
)
async def create_text_to_video(
    payload: TextToVideoRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service),
) -> GenerationBaseResponse:
    """Текст в видео."""
    try:
        job = await service.create_job(
            current_user,
            GenerationKind.TEXT_TO_VIDEO,
            "fal-ai/wan-25-preview/text-to-video",
            payload.model_dump(exclude_none=True),
            duration=payload.duration,
        )
    except InsufficientBalance:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="insufficient balance",
        )
    await session.commit()
    maybe_run_background(
        request.app.state.task_manager,
        lambda: run_generation_job(
            job.id, request.app.state.fal_client_factory
        ),
    )
    return job_response(job)


@router.post(
    "/videos/image-to-video",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=GenerationBaseResponse,
)
async def create_image_to_video(
    payload: ImageToVideoRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service),
) -> GenerationBaseResponse:
    """Изображение в видео."""
    try:
        job = await service.create_job(
            current_user,
            GenerationKind.IMAGE_TO_VIDEO,
            "fal-ai/wan-25-preview/image-to-video",
            payload.model_dump(exclude_none=True),
            duration=payload.duration,
        )
    except InsufficientBalance:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="insufficient balance",
        )
    await session.commit()
    maybe_run_background(
        request.app.state.task_manager,
        lambda: run_generation_job(
            job.id, request.app.state.fal_client_factory
        ),
    )
    return job_response(job)


@router.get("/{job_id}", response_model=GenerationDetailResponse)
async def get_generation(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service),
) -> GenerationDetailResponse:
    """Получить задачу."""
    job = await service.get_job(job_id, current_user)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="job not found"
        )
    return detail_response(job)


@router.get("", response_model=ListGenerationsResponse)
async def list_generations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service),
) -> ListGenerationsResponse:
    """Список задач."""
    jobs = await service.list_jobs(current_user, limit, offset)
    items = [detail_response(job) for job in jobs]
    return ListGenerationsResponse(items=items, limit=limit, offset=offset)


@router.post("/{job_id}/cancel", response_model=GenerationDetailResponse)
async def cancel_generation(
    job_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service),
) -> GenerationDetailResponse:
    """Отменить задачу."""
    job = await service.get_job(job_id, current_user)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="job not found"
        )
    if job.status in {
        GenerationStatus.COMPLETED,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELED,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cannot cancel finished job",
        )

    if job.fal_request_id and job.status in {
        GenerationStatus.IN_QUEUE,
        GenerationStatus.SUBMITTED,
    }:
        fal_client = (
            request.app.state.fal_client_factory()
            if request.app.state.fal_client_factory
            else HttpFalClient()
        )
        try:
            cancel_url = job.cancel_url or build_cancel_url(
                job.model_id, job.fal_request_id
            )
            await fal_client.cancel(cancel_url)
        finally:
            await fal_client.client.aclose()
    await service.refund_job(
        job, error_message="canceled", status=GenerationStatus.CANCELED
    )
    job.status = GenerationStatus.CANCELED
    return detail_response(job)
