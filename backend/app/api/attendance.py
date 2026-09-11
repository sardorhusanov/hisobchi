from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from app.api.dependencies import current_user, require_session
from app.models.entities import Attendance, User
from app.services.attendance import AttendanceNotFound, AttendanceService, AttendanceServiceError
from app.services.authorization import PermissionDenied, can_view_members
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/members", tags=["attendance"])


class AttendanceCreate(BaseModel):
    attendance_date: date
    units: Decimal | int | float = Field(default=0, ge=0, le=2)
    note: str | None = None


class AttendanceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    member_id: UUID
    year: int
    month: int
    attendance_units: int
    days_present: float
    estimated_salary_uzs: int
    monthly_salary_uzs: int


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    attendance_date: date
    units: int
    note: str | None = None


def _service_error(error: AttendanceServiceError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if isinstance(error, AttendanceNotFound)
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=code, detail=str(error))


@router.get("/{member_id}/attendance", response_model=list[AttendanceResponse])
async def list_attendance(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    member_id: UUID,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> list[Attendance]:
    if not can_view_members(user):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view attendance",
        )
    try:
        return await AttendanceService(session).list_attendance(
            member_id=member_id,
            start_date=start_date,
            end_date=end_date,
        )
    except AttendanceServiceError as error:
        raise _service_error(error) from error


@router.post(
    "/{member_id}/attendance",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_attendance(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    member_id: UUID,
    payload: AttendanceCreate,
) -> Attendance:
    if not can_view_members(user):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to update attendance",
        )
    try:
        record = await AttendanceService(session).upsert_attendance(
            actor=user,
            member_id=member_id,
            attendance_date=payload.attendance_date,
            units=payload.units,
            note=payload.note,
        )
        await session.commit()
        return record
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except AttendanceServiceError as error:
        await session.rollback()
        raise _service_error(error) from error


@router.get("/{member_id}/attendance/summary", response_model=AttendanceSummary)
async def attendance_summary(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    member_id: UUID,
    year: int = Query(..., ge=2000),
    month: int = Query(..., ge=1, le=12),
) -> dict[str, int | float | Decimal | None]:
    if not can_view_members(user):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view attendance",
        )
    try:
        result = await AttendanceService(session).month_summary(
            member_id=member_id,
            year=year,
            month=month,
        )
        return AttendanceSummary.model_validate(result)
    except AttendanceServiceError as error:
        raise _service_error(error) from error
