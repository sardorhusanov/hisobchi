from datetime import date
from typing import Annotated
from uuid import UUID

from app.api.dependencies import current_user, require_session
from app.models.entities import (
    FinancialTransaction,
    Member,
    Project,
    ProjectStatus,
    TransactionType,
    User,
)
from app.services.authorization import PermissionDenied, can_view_members
from app.services.projects import (
    FinanceService,
    FinanceServiceError,
    ProjectNotFound,
    ProjectService,
    ProjectServiceError,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1", tags=["projects", "finance"])


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    status: ProjectStatus = ProjectStatus.ACTIVE
    notes: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: ProjectStatus | None = None
    notes: str | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: ProjectStatus
    notes: str | None


class MemberBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    role: str


class TransactionCreate(BaseModel):
    transaction_type: TransactionType
    amount_uzs: int = Field(gt=0)
    transaction_date: date
    project_id: UUID | None = None
    category: str | None = Field(default=None, max_length=100)
    note: str | None = None
    idempotency_key: str | None = Field(default=None, max_length=255)


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_type: TransactionType
    amount_uzs: int
    transaction_date: date
    project_id: UUID | None
    category: str | None
    note: str | None
    idempotency_key: str | None


class FinanceSummary(BaseModel):
    year: int
    month: int
    income_uzs: int
    expense_uzs: int
    net_cashflow_uzs: int


def _project_error(error: ProjectServiceError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if isinstance(error, ProjectNotFound)
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=code, detail=str(error))


def _finance_error(error: FinanceServiceError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _require_view(user: User) -> None:
    if not can_view_members(user):
        raise PermissionDenied("You do not have permission to view projects or finance")


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    project_status: ProjectStatus | None = Query(default=None, alias="status"),
) -> list[Project]:
    try:
        _require_view(user)
        return await ProjectService(session).list_projects(status=project_status)
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    payload: ProjectCreate,
) -> Project:
    try:
        project = await ProjectService(session).create_project(actor=user, **payload.model_dump())
        await session.commit()
        return project
    except ProjectServiceError as error:
        await session.rollback()
        raise _project_error(error) from error


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    project_id: UUID,
    payload: ProjectUpdate,
) -> Project:
    try:
        project = await ProjectService(session).update_project(
            actor=user, project_id=project_id, **payload.model_dump(exclude_unset=True)
        )
        await session.commit()
        return project
    except ProjectServiceError as error:
        await session.rollback()
        raise _project_error(error) from error


@router.get("/projects/{project_id}/members", response_model=list[MemberBrief])
async def project_members(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    project_id: UUID,
) -> list[Member]:
    try:
        _require_view(user)
        return await ProjectService(session).project_members(project_id)
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ProjectServiceError as error:
        raise _project_error(error) from error


@router.post("/projects/{project_id}/members/{member_id}", status_code=status.HTTP_201_CREATED)
async def assign_member(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    project_id: UUID,
    member_id: UUID,
) -> dict[str, UUID]:
    try:
        assignment = await ProjectService(session).assign_member(
            actor=user, project_id=project_id, member_id=member_id
        )
        await session.commit()
        return {"project_id": assignment.project_id, "member_id": assignment.member_id}
    except ProjectServiceError as error:
        await session.rollback()
        raise _project_error(error) from error


@router.delete("/projects/{project_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    project_id: UUID,
    member_id: UUID,
) -> None:
    try:
        await ProjectService(session).remove_member(
            actor=user, project_id=project_id, member_id=member_id
        )
        await session.commit()
    except ProjectServiceError as error:
        await session.rollback()
        raise _project_error(error) from error


@router.get("/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
) -> list[FinancialTransaction]:
    try:
        _require_view(user)
        return await FinanceService(session).list_transactions(
            start_date=start_date, end_date=end_date, project_id=project_id
        )
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.post(
    "/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED
)
async def create_transaction(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    payload: TransactionCreate,
) -> FinancialTransaction:
    try:
        transaction = await FinanceService(session).create_transaction(
            actor=user, **payload.model_dump()
        )
        await session.commit()
        return transaction
    except FinanceServiceError as error:
        await session.rollback()
        raise _finance_error(error) from error


@router.get("/finance/summary", response_model=FinanceSummary)
async def finance_summary(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    year: int = Query(..., ge=2000),
    month: int = Query(..., ge=1, le=12),
) -> dict[str, int]:
    try:
        _require_view(user)
        return await FinanceService(session).monthly_summary(year=year, month=month)
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
