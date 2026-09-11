from datetime import datetime
from typing import Annotated
from uuid import UUID

from app.api.dependencies import current_user, require_session
from app.models.entities import MonthlyPayroll, PayrollPayment, User
from app.services.authorization import PermissionDenied, can_view_members
from app.services.payroll import PayrollNotFound, PayrollService, PayrollServiceError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1", tags=["payroll", "reports"])


class PayrollResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    year: int
    month: int
    salary_snapshot_uzs: int
    attendance_units: float
    earned_amount_uzs: int


class PaymentCreate(BaseModel):
    amount_uzs: int = Field(gt=0)
    note: str | None = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payroll_id: UUID
    amount_uzs: int
    paid_at: datetime
    note: str | None


class MonthlyReport(BaseModel):
    year: int
    month: int
    income_uzs: int
    expense_uzs: int
    net_cashflow_uzs: int
    payroll_uzs: int
    profit_uzs: int
    workers_count: int


def _error(error: PayrollServiceError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if isinstance(error, PayrollNotFound)
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=code, detail=str(error))


def _require_view(user: User) -> None:
    if not can_view_members(user):
        raise PermissionDenied("You do not have permission to view payroll or reports")


@router.get("/payroll", response_model=list[PayrollResponse])
async def list_payroll(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    year: int = Query(..., ge=2000),
    month: int = Query(..., ge=1, le=12),
) -> list[MonthlyPayroll]:
    try:
        _require_view(user)
        return await PayrollService(session).list_payroll(year=year, month=month)
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.post("/payroll/finalize", response_model=list[PayrollResponse])
async def finalize_payroll(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    year: int = Query(..., ge=2000),
    month: int = Query(..., ge=1, le=12),
) -> list[MonthlyPayroll]:
    try:
        rows = await PayrollService(session).finalize_month(actor=user, year=year, month=month)
        await session.commit()
        return rows
    except PayrollServiceError as error:
        await session.rollback()
        raise _error(error) from error


@router.post(
    "/payroll/{payroll_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_payment(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    payroll_id: UUID,
    payload: PaymentCreate,
) -> PayrollPayment:
    try:
        payment = await PayrollService(session).record_payment(
            actor=user, payroll_id=payroll_id, **payload.model_dump()
        )
        await session.commit()
        return payment
    except PayrollServiceError as error:
        await session.rollback()
        raise _error(error) from error


@router.get("/reports/monthly", response_model=MonthlyReport)
async def monthly_report(
    session: Annotated[AsyncSession, Depends(require_session)],
    user: Annotated[User, Depends(current_user)],
    year: int = Query(..., ge=2000),
    month: int = Query(..., ge=1, le=12),
) -> dict[str, int]:
    try:
        _require_view(user)
        return await PayrollService(session).monthly_report(year=year, month=month)
    except PermissionDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
