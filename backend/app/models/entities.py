from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Role(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    OWNER = "OWNER"
    PARTNER = "PARTNER"
    WORKER = "WORKER"


class MemberType(StrEnum):
    WORKER = "WORKER"
    OWNER = "OWNER"
    PARTNER = "PARTNER"


class ProjectStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class TransactionType(StrEnum):
    PROJECT_INCOME = "PROJECT_INCOME"
    PROJECT_EXPENSE = "PROJECT_EXPENSE"
    GENERAL_EXPENSE = "GENERAL_EXPENSE"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    telegram_user_id: Mapped[int] = mapped_column(unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(String(20), default=Role.WORKER)
    is_active: Mapped[bool] = mapped_column(default=True)


class Member(TimestampMixin, Base):
    __tablename__ = "members"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    full_name: Mapped[str] = mapped_column(String(255))
    member_type: Mapped[MemberType] = mapped_column(String(20))
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    user: Mapped[User | None] = relationship()
    salary_history: Mapped[list[SalaryHistory]] = relationship(cascade="all, delete-orphan")


class SalaryHistory(TimestampMixin, Base):
    __tablename__ = "salary_history"
    __table_args__ = (UniqueConstraint("member_id", "effective_from"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    member_id: Mapped[UUID] = mapped_column(ForeignKey("members.id"), index=True)
    monthly_salary_uzs: Mapped[int] = mapped_column(CheckConstraint("monthly_salary_uzs > 0"))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[ProjectStatus] = mapped_column(String(20), default=ProjectStatus.ACTIVE)
    notes: Mapped[str | None] = mapped_column(Text)


class ProjectMember(TimestampMixin, Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "member_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    member_id: Mapped[UUID] = mapped_column(ForeignKey("members.id"), index=True)


class Attendance(TimestampMixin, Base):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("member_id", "attendance_date"),
        CheckConstraint("units IN (0.0, 0.5, 1.0)"),
        Index("ix_attendance_date", "attendance_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    member_id: Mapped[UUID] = mapped_column(ForeignKey("members.id"), index=True)
    attendance_date: Mapped[date] = mapped_column(Date)
    units: Mapped[Decimal] = mapped_column(Numeric(2, 1))
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"))
    note: Mapped[str | None] = mapped_column(Text)


class FinancialTransaction(TimestampMixin, Base):
    __tablename__ = "financial_transactions"
    __table_args__ = (CheckConstraint("amount_uzs > 0"), Index("ix_transactions_date", "transaction_date"))

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    transaction_type: Mapped[TransactionType] = mapped_column(String(30))
    amount_uzs: Mapped[int]
    transaction_date: Mapped[date] = mapped_column(Date)
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"))
    category: Mapped[str | None] = mapped_column(String(100))
    note: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True)


class MonthlyPayroll(TimestampMixin, Base):
    __tablename__ = "monthly_payroll"
    __table_args__ = (UniqueConstraint("member_id", "year", "month"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    member_id: Mapped[UUID] = mapped_column(ForeignKey("members.id"), index=True)
    year: Mapped[int]
    month: Mapped[int]
    salary_snapshot_uzs: Mapped[int]
    attendance_units: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    earned_amount_uzs: Mapped[int]


class PayrollPayment(TimestampMixin, Base):
    __tablename__ = "payroll_payments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payroll_id: Mapped[UUID] = mapped_column(ForeignKey("monthly_payroll.id"), index=True)
    amount_uzs: Mapped[int] = mapped_column(CheckConstraint("amount_uzs > 0"))
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)


class ProfitDistribution(TimestampMixin, Base):
    __tablename__ = "profit_distributions"
    __table_args__ = (UniqueConstraint("year", "month"), CheckConstraint("profit_uzs >= 0"))

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    year: Mapped[int]
    month: Mapped[int]
    profit_uzs: Mapped[int]
    owner_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    partner_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    owner_amount_uzs: Mapped[int]
    partner_amount_uzs: Mapped[int]
    is_loss: Mapped[bool] = mapped_column(default=False)
