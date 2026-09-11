from datetime import datetime
from typing import Annotated
from uuid import UUID

from app.api.dependencies import current_user, require_session
from app.models.entities import AuditLog, User
from app.services.audit import AuditService
from app.services.authorization import can_view_members
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


class AuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, object]
    created_at: datetime


@router.get("", response_model=list[AuditResponse])
async def list_audit_entries(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditLog]:
    if not can_view_members(user):
        raise HTTPException(
            status_code=403, detail="You do not have permission to view audit history"
        )
    return await AuditService(session).list_entries(
        entity_type=entity_type,
        action=action,
        limit=limit,
    )
