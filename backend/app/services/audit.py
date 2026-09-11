from uuid import UUID

from app.models.entities import AuditLog, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AuditService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        *,
        actor: User | None,
        action: str,
        entity_type: str,
        entity_id: UUID | str | None,
        details: dict[str, object] | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_user_id=None if actor is None else actor.id,
            action=action,
            entity_type=entity_type,
            entity_id=None if entity_id is None else str(entity_id),
            details=details or {},
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_entries(
        self,
        *,
        entity_type: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        filters = []
        if entity_type is not None:
            filters.append(AuditLog.entity_type == entity_type)
        if action is not None:
            filters.append(AuditLog.action == action)
        return list(
            (
                await self.session.scalars(
                    select(AuditLog)
                    .where(*filters)
                    .order_by(AuditLog.created_at.desc())
                    .limit(limit)
                )
            ).all()
        )
