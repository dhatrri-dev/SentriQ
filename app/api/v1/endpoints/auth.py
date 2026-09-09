from datetime import timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserAuthResponse
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User successfully registered and authenticated"},
        400: {"model": ErrorResponse, "description": "Email already registered"},
    },
    summary="Register a new user / analyst account",
    description="Registers a user with a hashed password and returns an initial JWT bearer token."
)
async def register_user(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    # 1. Check if email already exists
    stmt = select(User).where(User.email == payload.email)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{payload.email}' is already registered."
        )

    # 2. Hash password & create user
    user = User(
        id=uuid4(),
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name or payload.email.split("@")[0].capitalize(),
        role=payload.role.upper(),
        is_active=True
    )
    db.add(user)
    await db.flush()

    # 3. Issue access token
    access_token = create_access_token(subject=user.id)
    user_response = UserAuthResponse.model_validate(user)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Login successful, access token returned"},
        401: {"model": ErrorResponse, "description": "Invalid email or password"},
    },
    summary="Authenticate user and obtain JWT token",
    description="Verifies user email and password, returning a signed JWT access token upon success."
)
async def login_user(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    stmt = select(User).where(User.email == payload.email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated."
        )

    access_token = create_access_token(subject=user.id)
    user_response = UserAuthResponse.model_validate(user)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response
    )


@router.get(
    "/me",
    response_model=UserAuthResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Current user profile fetched successfully"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
    summary="Get current signed-in user profile",
    description="Returns identity and profile information for the currently authenticated user."
)
async def get_me(
    current_user: User = Depends(get_current_user)
) -> UserAuthResponse:
    return UserAuthResponse.model_validate(current_user)
