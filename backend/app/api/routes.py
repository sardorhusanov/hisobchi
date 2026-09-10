from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_session
from app.core.config import Settings, get_settings
from app.core.security import TelegramInitDataError, create_access_token, validate_telegram_init_data
from app.models.entities import Role, User

router = APIRouter(prefix="/api/v1")


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(min_length=1)


class TelegramAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


@router.post("/auth/telegram", response_model=TelegramAuthResponse)
async def authenticate_telegram(
    payload: TelegramAuthRequest,
    session: AsyncSession = Depends(require_session),
    settings: Settings = Depends(get_settings),
) -> TelegramAuthResponse:
    try:
        validated = validate_telegram_init_data(payload.init_data, settings)
    except (TelegramInitDataError, ValueError) as error:
        raise HTTPException(status_code=401, detail="Invalid Telegram authentication data") from error

    telegram_user = validated["user"]
    telegram_id = int(telegram_user["id"])
    user = await session.scalar(select(User).where(User.telegram_user_id == telegram_id))
    if user is None:
        role = Role.SUPER_ADMIN if telegram_id == settings.super_admin_telegram_id else Role.WORKER
        user = User(
            telegram_user_id=telegram_id,
            username=telegram_user.get("username"),
            role=role,
        )
        session.add(user)
        await session.commit()
    elif not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    return TelegramAuthResponse(access_token=create_access_token(telegram_id, settings), role=user.role)
