from datetime import date

import pytest
from app.models.entities import (
    Attendance,
    Base,
    EmploymentStatus,
    Member,
    MemberType,
    Role,
    SalaryHistory,
    User,
)
from app.services.payroll import PayrollService, PayrollServiceError
from app.services.projects import FinanceService
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
async def payroll_context(session):
    admin = User(telegram_user_id=100, role=Role.SUPER_ADMIN)
    worker = Member(
        full_name="Worker",
        member_type=MemberType.WORKER,
        role=Role.WORKER,
        employment_status=EmploymentStatus.ACTIVE,
        joined_on=date(2026, 9, 1),
    )
    session.add_all([admin, worker])
    await session.flush()
    session.add(
        SalaryHistory(
            member_id=worker.id,
            monthly_salary_uzs=6_000_000,
            effective_from=date(2026, 9, 1),
            created_by_user_id=admin.id,
        )
    )
    session.add_all(
        [
            Attendance(member_id=worker.id, attendance_date=date(2026, 9, 1), units=2),
            Attendance(member_id=worker.id, attendance_date=date(2026, 9, 2), units=1),
        ]
    )
    await session.flush()
    return admin, worker


@pytest.mark.asyncio
async def test_finalize_payroll_and_monthly_report(session, payroll_context):
    admin, worker = payroll_context
    await FinanceService(session).create_transaction(
        actor=admin,
        transaction_type="PROJECT_INCOME",
        amount_uzs=10_000_000,
        transaction_date=date(2026, 9, 1),
        project_id=None,
        category=None,
        note=None,
        idempotency_key=None,
    )
    payroll_service = PayrollService(session)
    rows = await payroll_service.finalize_month(actor=admin, year=2026, month=9)
    assert len(rows) == 1
    assert rows[0].member_id == worker.id
    assert rows[0].attendance_units == 3
    assert rows[0].earned_amount_uzs == 300_000
    report = await payroll_service.monthly_report(year=2026, month=9)
    assert report["payroll_uzs"] == 300_000
    assert report["profit_uzs"] == 9_700_000


@pytest.mark.asyncio
async def test_payments_cannot_exceed_finalized_payroll(session, payroll_context):
    admin, _ = payroll_context
    payroll = (await PayrollService(session).finalize_month(actor=admin, year=2026, month=9))[0]
    with pytest.raises(PayrollServiceError, match="exceed"):
        await PayrollService(session).record_payment(
            actor=admin,
            payroll_id=payroll.id,
            amount_uzs=300_001,
            note=None,
        )
