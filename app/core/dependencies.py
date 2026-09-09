from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

# HTTP Bearer Token Scheme (optional header parsing to allow explicit 401 handling)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Returns the current authenticated user if a valid Bearer token is supplied; otherwise returns None."""
    if not auth or not auth.credentials:
        return None

    payload = decode_access_token(auth.credentials)
    if not payload or "sub" not in payload:
        return None

    sub = payload["sub"]
    try:
        user_id = UUID(sub)
        stmt = select(User).where(User.id == user_id)
    except (ValueError, TypeError):
        stmt = select(User).where(User.email == str(sub))

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None

    return user


async def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """Dependency that strictly requires a valid authenticated user. Rejects anonymous requests with 401 Unauthorized."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or missing Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
