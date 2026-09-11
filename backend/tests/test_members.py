from datetime import date
from uuid import uuid4

import pytest
from app.models.entities import Base, EmploymentStatus, Role, User
from app.services.authorization import PermissionDenied
from app.services.members import MemberService, MemberServiceError, SalaryPeriodOverlap
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


@pytest.fixture
async def admin(session):
    user = User(telegram_user_id=100, role=Role.SUPER_ADMIN)
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_member_creation_and_deactivation(session, admin):
    service = MemberService(session)
    member = await service.create_member(
        actor=admin,
        full_name="Ali Valiyev",
        role=Role.WORKER,
        phone_number=None,
        telegram_user_id=555,
        employment_status=EmploymentStatus.ACTIVE,
        joined_on=date(2026, 1, 1),
        ended_on=None,
        notes=None,
    )
    await service.deactivate_member(actor=admin, member_id=member.id, ended_on=date(2026, 9, 10))
    assert member.employment_status == EmploymentStatus.INACTIVE
    assert member.ended_on == date(2026, 9, 10)


@pytest.mark.asyncio
async def test_duplicate_telegram_ids_are_rejected(session, admin):
    service = MemberService(session)
    await service.create_member(
        actor=admin,
        full_name="First",
        role=Role.WORKER,
        phone_number=None,
        telegram_user_id=777,
        employment_status=EmploymentStatus.ACTIVE,
        joined_on=date(2026, 1, 1),
        ended_on=None,
        notes=None,
    )
    with pytest.raises(MemberServiceError, match="already linked"):
        await service.create_member(
            actor=admin,
            full_name="Second",
            role=Role.WORKER,
            phone_number=None,
            telegram_user_id=777,
            employment_status=EmploymentStatus.ACTIVE,
            joined_on=date(2026, 1, 1),
            ended_on=None,
            notes=None,
        )


@pytest.mark.asyncio
async def test_worker_salary_history_closes_previous_period(session, admin):
    service = MemberService(session)
    member = await service.create_member(
        actor=admin,
        full_name="Worker",
        role=Role.WORKER,
        phone_number=None,
        telegram_user_id=None,
        employment_status=EmploymentStatus.ACTIVE,
        joined_on=date(2026, 1, 1),
        ended_on=None,
        notes=None,
    )
    first = await service.create_salary(
        actor=admin,
        member_id=member.id,
        monthly_salary_uzs=6_000_000,
        effective_from=date(2026, 1, 1),
        effective_to=None,
    )
    second = await service.create_salary(
        actor=admin,
        member_id=member.id,
        monthly_salary_uzs=7_000_000,
        effective_from=date(2026, 7, 1),
        effective_to=None,
    )
    assert first.effective_to == date(2026, 6, 30)
    assert second.monthly_salary_uzs == 7_000_000


@pytest.mark.asyncio
async def test_salary_overlap_and_owner_salary_are_rejected(session, admin):
    service = MemberService(session)
    worker = await service.create_member(
        actor=admin,
        full_name="Worker",
        role=Role.WORKER,
        phone_number=None,
        telegram_user_id=None,
        employment_status=EmploymentStatus.ACTIVE,
        joined_on=date(2026, 1, 1),
        ended_on=None,
        notes=None,
    )
    await service.create_salary(
        actor=admin,
        member_id=worker.id,
        monthly_salary_uzs=1,
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
    )
    with pytest.raises(SalaryPeriodOverlap):
        await service.create_salary(
            actor=admin,
            member_id=worker.id,
            monthly_salary_uzs=2,
            effective_from=date(2026, 6, 1),
            effective_to=None,
        )
    owner = await service.create_member(
        actor=admin,
        full_name="Owner",
        role=Role.OWNER,
        phone_number=None,
        telegram_user_id=None,
        employment_status=EmploymentStatus.ACTIVE,
        joined_on=date(2026, 1, 1),
        ended_on=None,
        notes=None,
    )
    with pytest.raises(MemberServiceError, match="Only workers"):
        await service.create_salary(
            actor=admin,
            member_id=owner.id,
            monthly_salary_uzs=1,
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )


@pytest.mark.asyncio
async def test_worker_cannot_manage_members(session):
    worker = User(id=uuid4(), telegram_user_id=101, role=Role.WORKER)
    session.add(worker)
    await session.flush()
    with pytest.raises(PermissionDenied):
        await MemberService(session).create_member(
            actor=worker,
            full_name="Nope",
            role=Role.WORKER,
            phone_number=None,
            telegram_user_id=None,
            employment_status=EmploymentStatus.ACTIVE,
            joined_on=date(2026, 1, 1),
            ended_on=None,
            notes=None,
        )
