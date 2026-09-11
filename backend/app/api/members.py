from datetime import date
from typing import Annotated
from uuid import UUID

from app.api.dependencies import current_user, require_session
from app.models.entities import EmploymentStatus, Member, Role, SalaryHistory, User
from app.services.authorization import PermissionDenied, can_view_members
from app.services.members import (
    MemberNotFound,
    MemberService,
    MemberServiceError,
    SalaryPeriodOverlap,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/members", tags=["members"])


class MemberCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    role: Role = Role.WORKER
    phone_number: str | None = Field(default=None, max_length=30)
    telegram_user_id: int | None = None
    employment_status: EmploymentStatus = EmploymentStatus.ACTIVE
    joined_on: date = Field(default_factory=date.today)
    ended_on: date | None = None
    notes: str | None = None


class MemberUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: Role | None = None
    phone_number: str | None = Field(default=None, max_length=30)
    employment_status: EmploymentStatus | None = None
    joined_on: date | None = None
    ended_on: date | None = None
    notes: str | None = None


class TelegramLink(BaseModel):
    telegram_user_id: int = Field(gt=0)


class SalaryCreate(BaseModel):
    monthly_salary_uzs: int = Field(ge=0)
    effective_from: date
    effective_to: date | None = None


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    role: Role
    phone_number: str | None
    telegram_user_id: int | None
    employment_status: EmploymentStatus
    joined_on: date
    ended_on: date | None
    notes: str | None


class SalaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    monthly_salary_uzs: int
    effective_from: date
    effective_to: date | None
    created_by_user_id: UUID | None


class MemberPage(BaseModel):
    items: list[MemberResponse]
    total: int
    offset: int
    limit: int


def _service_error(error: MemberServiceError) -> HTTPException:
    code = (
        status.HTTP_409_CONFLICT
        if isinstance(error, SalaryPeriodOverlap) or "already linked" in str(error)
        else status.HTTP_400_BAD_REQUEST
    )
    if isinstance(error, MemberNotFound):
        code = status.HTTP_404_NOT_FOUND
    return HTTPException(status_code=code, detail=str(error))


def _ensure_view_access(user: User) -> None:
    if not can_view_members(user):
        raise PermissionDenied("You do not have permission to view members")


@router.get("", response_model=MemberPage)
async def list_members(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    role: Role | None = None,
    active: bool | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> MemberPage:
    try:
        _ensure_view_access(user)
        members, total = await MemberService(session).list_members(
            role=role,
            active=active,
            offset=offset,
            limit=limit,
        )
        return MemberPage(
            items=[MemberResponse.model_validate(member) for member in members],
            total=total,
            offset=offset,
            limit=limit,
        )
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.post("", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def create_member(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    payload: MemberCreate,
) -> Member:
    try:
        member = await MemberService(session).create_member(actor=user, **payload.model_dump())
        await session.commit()
        return member
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except MemberServiceError as error:
        await session.rollback()
        raise _service_error(error) from error


@router.get("/{member_id}", response_model=MemberResponse)
async def get_member(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    member_id: UUID,
) -> Member:
    try:
        _ensure_view_access(user)
        return await MemberService(session).get_member(member_id)
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except MemberServiceError as error:
        raise _service_error(error) from error


@router.patch("/{member_id}", response_model=MemberResponse)
async def update_member(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    member_id: UUID,
    payload: MemberUpdate,
) -> Member:
    try:
        member = await MemberService(session).update_member(
            actor=user,
            member_id=member_id,
            **payload.model_dump(exclude_unset=True),
        )
        await session.commit()
        return member
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except MemberServiceError as error:
        await session.rollback()
        raise _service_error(error) from error


@router.post("/{member_id}/deactivate", response_model=MemberResponse)
async def deactivate_member(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    member_id: UUID,
    ended_on: date | None = None,
) -> Member:
    try:
        member = await MemberService(session).deactivate_member(
            actor=user,
            member_id=member_id,
            ended_on=ended_on,
        )
        await session.commit()
        return member
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except MemberServiceError as error:
        await session.rollback()
        raise _service_error(error) from error


@router.post("/{member_id}/telegram", response_model=MemberResponse)
async def link_telegram(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    member_id: UUID,
    payload: TelegramLink,
) -> Member:
    try:
        member = await MemberService(session).link_telegram(
            actor=user,
            member_id=member_id,
            telegram_user_id=payload.telegram_user_id,
        )
        await session.commit()
        return member
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except MemberServiceError as error:
        await session.rollback()
        raise _service_error(error) from error


@router.delete("/{member_id}/telegram", response_model=MemberResponse)
async def unlink_telegram(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    member_id: UUID,
) -> Member:
    try:
        member = await MemberService(session).unlink_telegram(actor=user, member_id=member_id)
        await session.commit()
        return member
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except MemberServiceError as error:
        await session.rollback()
        raise _service_error(error) from error


@router.post(
    "/{member_id}/salary",
    response_model=SalaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_salary(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    member_id: UUID,
    payload: SalaryCreate,
) -> SalaryHistory:
    try:
        salary = await MemberService(session).create_salary(
            actor=user,
            member_id=member_id,
            **payload.model_dump(),
        )
        await session.commit()
        return salary
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except MemberServiceError as error:
        await session.rollback()
        raise _service_error(error) from error


@router.get("/{member_id}/salary", response_model=list[SalaryResponse])
async def salary_history(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    member_id: UUID,
) -> list[SalaryHistory]:
    try:
        _ensure_view_access(user)
        return await MemberService(session).salary_history(member_id)
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except MemberServiceError as error:
        raise _service_error(error) from error
