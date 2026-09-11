from datetime import date
from uuid import uuid4

import pytest
from app.models.entities import Base, Role, TransactionType, User
from app.services.projects import (
    FinanceService,
    FinanceServiceError,
    ProjectService,
    ProjectServiceError,
)
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
async def test_project_assignment_and_finance_summary(session, admin):
    service = ProjectService(session)
    project = await service.create_project(
        actor=admin, name="Kitchen renovation", status="ACTIVE", notes=None
    )
    worker = await ProjectService(session).session.get(type(project), project.id)
    assert worker is not None

    finance = FinanceService(session)
    await finance.create_transaction(
        actor=admin,
        transaction_type=TransactionType.PROJECT_INCOME,
        amount_uzs=10_000_000,
        transaction_date=date(2026, 9, 1),
        project_id=project.id,
        category=None,
        note=None,
        idempotency_key="income-1",
    )
    await finance.create_transaction(
        actor=admin,
        transaction_type=TransactionType.PROJECT_EXPENSE,
        amount_uzs=3_000_000,
        transaction_date=date(2026, 9, 2),
        project_id=project.id,
        category="Materials",
        note=None,
        idempotency_key="expense-1",
    )
    summary = await finance.monthly_summary(year=2026, month=9)
    assert summary["income_uzs"] == 10_000_000
    assert summary["expense_uzs"] == 3_000_000
    assert summary["net_cashflow_uzs"] == 7_000_000


@pytest.mark.asyncio
async def test_finance_rejects_invalid_project_and_duplicate_is_idempotent(session, admin):
    finance = FinanceService(session)
    with pytest.raises(FinanceServiceError, match="Project not found"):
        await finance.create_transaction(
            actor=admin,
            transaction_type=TransactionType.GENERAL_EXPENSE,
            amount_uzs=1,
            transaction_date=date(2026, 9, 1),
            project_id=uuid4(),
            category=None,
            note=None,
            idempotency_key=None,
        )

    first = await finance.create_transaction(
        actor=admin,
        transaction_type=TransactionType.GENERAL_EXPENSE,
        amount_uzs=2,
        transaction_date=date(2026, 9, 1),
        project_id=None,
        category=None,
        note=None,
        idempotency_key="same",
    )
    second = await finance.create_transaction(
        actor=admin,
        transaction_type=TransactionType.GENERAL_EXPENSE,
        amount_uzs=99,
        transaction_date=date(2026, 9, 2),
        project_id=None,
        category=None,
        note=None,
        idempotency_key="same",
    )
    assert second.id == first.id
    assert second.amount_uzs == 2


@pytest.mark.asyncio
async def test_worker_cannot_manage_projects(session):
    worker = User(telegram_user_id=101, role=Role.WORKER)
    session.add(worker)
    await session.flush()
    with pytest.raises(ProjectServiceError, match="Only super admin"):
        await ProjectService(session).create_project(
            actor=worker, name="Nope", status="ACTIVE", notes=None
        )
