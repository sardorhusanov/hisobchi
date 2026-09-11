from typing import Annotated

from app.core.config import Settings, get_settings
from app.core.security import AccessTokenError, decode_access_token
from app.db.session import get_session
from app.models.entities import User
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def require_session(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncSession:
    return session


async def bearer_token(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return authorization.removeprefix("Bearer ").strip()


async def current_user(
    token: Annotated[str, Depends(bearer_token)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    try:
        telegram_user_id = decode_access_token(token, settings)
    except AccessTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        ) from error

    user = await session.scalar(
        select(User).where(
            User.telegram_user_id == telegram_user_id,
            User.is_active.is_(True),
        )
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
