from datetime import date

import pytest
from app.models.entities import AuditLog, Base, EmploymentStatus, Role, User
from app.services.audit import AuditService
from app.services.members import MemberService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_member_mutation_is_audited(session):
    admin = User(telegram_user_id=100, role=Role.SUPER_ADMIN)
    session.add(admin)
    await session.flush()
    member = await MemberService(session).create_member(
        actor=admin,
        full_name="Audit Worker",
        role=Role.WORKER,
        phone_number=None,
        telegram_user_id=None,
        employment_status=EmploymentStatus.ACTIVE,
        joined_on=date(2026, 9, 1),
        ended_on=None,
        notes=None,
    )
    entries = await AuditService(session).list_entries(entity_type="member")
    assert len(entries) == 1
    assert entries[0].action == "member.created"
    assert entries[0].entity_id == str(member.id)
    assert entries[0].actor_user_id == admin.id


@pytest.mark.asyncio
async def test_audit_filters_and_details(session):
    admin = User(telegram_user_id=100, role=Role.SUPER_ADMIN)
    session.add(admin)
    await session.flush()
    await AuditService(session).record(
        actor=admin,
        action="test.created",
        entity_type="test",
        entity_id=None,
        details={"value": 1},
    )
    entry = await session.scalar(select(AuditLog).where(AuditLog.entity_type == "test"))
    assert entry is not None
    assert entry.details == {"value": 1}
    assert await AuditService(session).list_entries(action="missing") == []
