from typing import Annotated

from app.api.attendance import router as attendance_router
from app.api.audit import router as audit_router
from app.api.dependencies import require_session
from app.api.members import router as members_router
from app.api.payroll import router as payroll_router
from app.api.projects import router as projects_router
from app.core.config import Settings, get_settings
from app.core.security import (
    TelegramInitDataError,
    create_access_token,
    validate_telegram_init_data,
)
from app.models.entities import Role, User
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1")
router.include_router(members_router)
router.include_router(attendance_router)
router.include_router(audit_router)
router.include_router(projects_router)
router.include_router(payroll_router)


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(min_length=1)


class TelegramAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


@router.post("/auth/telegram", response_model=TelegramAuthResponse)
async def authenticate_telegram(
    session: Annotated[AsyncSession, Depends(require_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    payload: TelegramAuthRequest,
) -> TelegramAuthResponse:
    try:
        validated = validate_telegram_init_data(payload.init_data, settings)
    except (TelegramInitDataError, ValueError) as error:
        raise HTTPException(
            status_code=401, detail="Invalid Telegram authentication data"
        ) from error

    telegram_user = validated["user"]
    telegram_id = int(telegram_user["id"])
    user = await session.scalar(select(User).where(User.telegram_user_id == telegram_id))
    if user is None:
        if telegram_id != settings.super_admin_telegram_id:
            raise HTTPException(
                status_code=403,
                detail="Telegram account is not linked. Ask an administrator to link your account.",
            )
        role = Role.SUPER_ADMIN
        user = User(
            telegram_user_id=telegram_id,
            username=telegram_user.get("username"),
            role=role,
        )
        session.add(user)
        await session.commit()
    elif not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    return TelegramAuthResponse(
        access_token=create_access_token(telegram_id, settings),
        role=user.role,
    )
