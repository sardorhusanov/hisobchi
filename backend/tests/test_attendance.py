from datetime import date

import pytest
from app.models.entities import Base, EmploymentStatus, Role, User
from app.services.attendance import AttendanceService, AttendanceServiceError
from app.services.members import MemberService
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
    user = User(telegram_user_id=200, role=Role.SUPER_ADMIN)
    session.add(user)
    await session.flush()
    return user


@pytest.fixture
async def worker(session, admin):
    service = MemberService(session)
    return await service.create_member(
        actor=admin,
        full_name="Ali Ismoilov",
        role=Role.WORKER,
        phone_number=None,
        telegram_user_id=777,
        employment_status=EmploymentStatus.ACTIVE,
        joined_on=date(2026, 1, 1),
        ended_on=None,
        notes=None,
    )


@pytest.mark.asyncio
async def test_attendance_tracks_half_day_units(session, admin, worker):
    service = AttendanceService(session)
    record = await service.upsert_attendance(
        actor=admin,
        member_id=worker.id,
        attendance_date=date(2026, 9, 10),
        units=1,
        note="Yarim kun",
    )
    assert record.units == 1
    assert record.note == "Yarim kun"

    summary = await service.month_summary(member_id=worker.id, year=2026, month=9)
    assert summary["attendance_units"] == 1
    assert summary["days_present"] == 0.5


@pytest.mark.asyncio
async def test_attendance_rejects_inactive_members(session, admin, worker):
    service = AttendanceService(session)
    member = await service.get_member(worker.id)
    member.employment_status = EmploymentStatus.INACTIVE
    member.is_active = False

    with pytest.raises(AttendanceServiceError, match="inactive"):
        await service.upsert_attendance(
            actor=admin,
            member_id=member.id,
            attendance_date=date(2026, 9, 11),
            units=2,
        )


@pytest.mark.asyncio
async def test_estimated_salary_uses_half_day_units(session, admin, worker):
    service = AttendanceService(session)
    member_service = MemberService(session)
    await member_service.create_salary(
        actor=admin,
        member_id=worker.id,
        monthly_salary_uzs=3_000_000,
        effective_from=date(2026, 9, 1),
        effective_to=None,
    )
    await service.upsert_attendance(
        actor=admin,
        member_id=worker.id,
        attendance_date=date(2026, 9, 1),
        units=2,
    )
    await service.upsert_attendance(
        actor=admin,
        member_id=worker.id,
        attendance_date=date(2026, 9, 2),
        units=1,
    )
    summary = await service.month_summary(member_id=worker.id, year=2026, month=9)
    assert summary["attendance_units"] == 3
    assert summary["estimated_salary_uzs"] == 150_000
