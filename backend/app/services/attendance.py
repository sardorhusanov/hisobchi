from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.models.entities import Attendance, EmploymentStatus, Member, SalaryHistory
from app.services.audit import AuditService
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


class AttendanceServiceError(ValueError):
    pass


class AttendanceNotFound(AttendanceServiceError):
    pass


class AttendanceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()

    async def get_member(self, member_id: UUID) -> Member:
        member = await self.session.get(Member, member_id)
        if member is None:
            raise AttendanceNotFound("Member not found")
        return member

    async def list_attendance(
        self,
        *,
        member_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Attendance]:
        await self.get_member(member_id)
        filters: list[Any] = [Attendance.member_id == member_id]
        if start_date is not None:
            filters.append(Attendance.attendance_date >= start_date)
        if end_date is not None:
            filters.append(Attendance.attendance_date <= end_date)
        return list(
            (
                await self.session.scalars(
                    select(Attendance).where(*filters).order_by(Attendance.attendance_date.desc())
                )
            ).all()
        )

    async def upsert_attendance(
        self,
        *,
        actor: Any,
        member_id: UUID,
        attendance_date: date,
        units: int | float | Decimal | str,
        note: str | None = None,
    ) -> Attendance:
        member = await self.get_member(member_id)
        if member.employment_status != EmploymentStatus.ACTIVE or not member.is_active:
            raise AttendanceServiceError("Member is inactive and cannot be marked present")
        if attendance_date < member.joined_on:
            raise AttendanceServiceError("Attendance date cannot be before member join date")
        if member.ended_on is not None and attendance_date > member.ended_on:
            raise AttendanceServiceError("Attendance date cannot be after member end date")
        normalized_units = self._normalize_units(units)
        record = await self.session.scalar(
            select(Attendance).where(
                Attendance.member_id == member_id,
                Attendance.attendance_date == attendance_date,
            )
        )
        if record is None:
            record = Attendance(
                member_id=member_id,
                attendance_date=attendance_date,
                units=normalized_units,
                note=note,
            )
            self.session.add(record)
        else:
            record.units = normalized_units
            record.note = note
        await self.session.flush()
        await AuditService(self.session).record(
            actor=actor,
            action="attendance.upserted",
            entity_type="attendance",
            entity_id=record.id,
            details={"member_id": str(member_id), "units": normalized_units},
        )
        return record

    async def month_summary(
        self,
        *,
        member_id: UUID,
        year: int,
        month: int,
    ) -> dict[str, int | float | None]:
        await self.get_member(member_id)
        month_start = date(year, month, 1)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        rows = list(
            (
                await self.session.scalars(
                    select(Attendance).where(
                        Attendance.member_id == member_id,
                        Attendance.attendance_date >= month_start,
                        Attendance.attendance_date < next_month,
                    )
                )
            ).all()
        )
        attendance_units = sum((row.units for row in rows), 0)
        days_present = Decimal(attendance_units) / Decimal(2)
        salary = await self.session.scalar(
            select(SalaryHistory.monthly_salary_uzs)
            .where(
                SalaryHistory.member_id == member_id,
                SalaryHistory.effective_from <= month_start,
                or_(
                    SalaryHistory.effective_to.is_(None), SalaryHistory.effective_to >= month_start
                ),
            )
            .order_by(SalaryHistory.effective_from.desc())
            .limit(1)
        )
        estimated_salary_uzs = (
            0
            if salary is None
            else int(
                (Decimal(salary) * days_present / Decimal(self.settings.salary_divisor)).quantize(
                    Decimal("1")
                )
            )
        )
        return {
            "member_id": member_id,
            "year": year,
            "month": month,
            "attendance_units": attendance_units,
            "days_present": float(days_present),
            "estimated_salary_uzs": estimated_salary_uzs,
            "monthly_salary_uzs": int(salary or 0),
        }

    @staticmethod
    def _normalize_units(units: int | float | Decimal | str) -> int:
        try:
            value = Decimal(str(units))
        except Exception as exc:  # pragma: no cover - defensive guard
            raise AttendanceServiceError("Invalid attendance units") from exc
        if value in {Decimal("0"), Decimal("0.0")}:
            return 0
        if value in {Decimal("0.5"), Decimal("1"), Decimal("1.0")}:
            return 1
        if value in {Decimal("2"), Decimal("2.0")}:
            return 2
        raise AttendanceServiceError("Attendance units must be 0, 0.5, or 1.0 day")
