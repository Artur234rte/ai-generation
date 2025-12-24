from fastapi import APIRouter, Depends, HTTPException, status

from app.application.use_cases.auth import AuthService, UserAlreadyExists
from app.presentation.api.dependencies import get_auth_service
from app.presentation.schemas.auth import AuthRequest, AuthResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    payload: AuthRequest, service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    """Регистрация или ротация ключа."""
    try:
        user, api_key = await service.register_or_rotate(
            payload.external_user_id, payload.rotate
        )
    except UserAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="already exists"
        )
    return AuthResponse(
        external_user_id=user.external_user_id, api_key=api_key
    )
