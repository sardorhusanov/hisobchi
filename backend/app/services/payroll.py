from calendar import monthrange
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from app.models.entities import (
    Attendance,
    Member,
    MonthlyPayroll,
    PayrollPayment,
    Role,
    SalaryHistory,
    User,
)
from app.services.audit import AuditService
from app.services.authorization import can_manage_members, can_view_members
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


class PayrollServiceError(ValueError):
    pass


class PayrollNotFound(PayrollServiceError):
    pass


class PayrollService:
    def __init__(self, session: AsyncSession, salary_divisor: int = 30):
        self.session = session
        self.salary_divisor = salary_divisor

    async def finalize_month(self, *, actor: User, year: int, month: int) -> list[MonthlyPayroll]:
        self._require_manage(actor)
        start_date, end_date = self._month_range(year, month)
        workers = list(
            (
                await self.session.scalars(
                    select(Member).where(Member.role == Role.WORKER).order_by(Member.full_name)
                )
            ).all()
        )
        result: list[MonthlyPayroll] = []
        for worker in workers:
            salary = await self._salary_for(worker.id, start_date)
            if salary is None:
                continue
            rows = list(
                (
                    await self.session.scalars(
                        select(Attendance).where(
                            Attendance.member_id == worker.id,
                            Attendance.attendance_date >= start_date,
                            Attendance.attendance_date <= end_date,
                        )
                    )
                ).all()
            )
            total_units = sum(row.units for row in rows)
            earned = int(
                (
                    Decimal(salary) * Decimal(total_units) / Decimal(2 * self.salary_divisor)
                ).quantize(Decimal("1"))
            )
            payroll = await self.session.scalar(
                select(MonthlyPayroll).where(
                    MonthlyPayroll.member_id == worker.id,
                    MonthlyPayroll.year == year,
                    MonthlyPayroll.month == month,
                )
            )
            if payroll is None:
                payroll = MonthlyPayroll(
                    member_id=worker.id,
                    year=year,
                    month=month,
                    salary_snapshot_uzs=salary,
                    attendance_units=Decimal(total_units),
                    earned_amount_uzs=earned,
                )
                self.session.add(payroll)
            else:
                payroll.salary_snapshot_uzs = salary
                payroll.attendance_units = Decimal(total_units)
                payroll.earned_amount_uzs = earned
            result.append(payroll)
        await self.session.flush()
        for payroll in result:
            await AuditService(self.session).record(
                actor=actor,
                action="payroll.finalized",
                entity_type="monthly_payroll",
                entity_id=payroll.id,
                details={"year": year, "month": month},
            )
        return result

    async def list_payroll(self, *, year: int, month: int) -> list[MonthlyPayroll]:
        return list(
            (
                await self.session.scalars(
                    select(MonthlyPayroll)
                    .where(MonthlyPayroll.year == year, MonthlyPayroll.month == month)
                    .order_by(MonthlyPayroll.created_at.desc())
                )
            ).all()
        )

    async def get_payroll(self, payroll_id: UUID) -> MonthlyPayroll:
        payroll = await self.session.get(MonthlyPayroll, payroll_id)
        if payroll is None:
            raise PayrollNotFound("Payroll record not found")
        return payroll

    async def record_payment(
        self,
        *,
        actor: User,
        payroll_id: UUID,
        amount_uzs: int,
        note: str | None,
    ) -> PayrollPayment:
        self._require_manage(actor)
        if amount_uzs <= 0:
            raise PayrollServiceError("Payment amount must be positive")
        payroll = await self.get_payroll(payroll_id)
        payments = list(
            (
                await self.session.scalars(
                    select(PayrollPayment.amount_uzs).where(PayrollPayment.payroll_id == payroll.id)
                )
            ).all()
        )
        if sum(payments) + amount_uzs > payroll.earned_amount_uzs:
            raise PayrollServiceError("Payments cannot exceed earned payroll")
        payment = PayrollPayment(
            payroll_id=payroll.id,
            amount_uzs=amount_uzs,
            paid_at=datetime.now(UTC),
            note=note,
        )
        self.session.add(payment)
        await self.session.flush()
        await AuditService(self.session).record(
            actor=actor,
            action="payroll.payment_recorded",
            entity_type="payroll_payment",
            entity_id=payment.id,
            details={"payroll_id": str(payroll_id), "amount_uzs": amount_uzs},
        )
        return payment

    async def monthly_report(self, *, year: int, month: int) -> dict[str, int]:
        from app.services.projects import FinanceService

        finance = await FinanceService(self.session).monthly_summary(year=year, month=month)
        payroll_rows = await self.list_payroll(year=year, month=month)
        payroll = sum(row.earned_amount_uzs for row in payroll_rows)
        return {
            **finance,
            "payroll_uzs": payroll,
            "profit_uzs": finance["net_cashflow_uzs"] - payroll,
            "workers_count": len(payroll_rows),
        }

    async def can_view(self, actor: User) -> bool:
        return can_view_members(actor)

    async def _salary_for(self, member_id: UUID, month_start: date) -> int | None:
        return await self.session.scalar(
            select(SalaryHistory.monthly_salary_uzs)
            .where(
                SalaryHistory.member_id == member_id,
                SalaryHistory.effective_from <= month_start,
                or_(
                    SalaryHistory.effective_to.is_(None),
                    SalaryHistory.effective_to >= month_start,
                ),
            )
            .order_by(SalaryHistory.effective_from.desc())
            .limit(1)
        )

    @staticmethod
    def _month_range(year: int, month: int) -> tuple[date, date]:
        if month not in range(1, 13):
            raise PayrollServiceError("Month must be between 1 and 12")
        return date(year, month, 1), date(year, month, monthrange(year, month)[1])

    @staticmethod
    def _require_manage(actor: User) -> None:
        if not can_manage_members(actor):
            raise PayrollServiceError("Only super admin or owner can manage payroll")
