from datetime import date
from uuid import UUID

from app.models.entities import (
    EmploymentStatus,
    FinancialTransaction,
    Member,
    Project,
    ProjectMember,
    ProjectStatus,
    TransactionType,
    User,
)
from app.services.audit import AuditService
from app.services.authorization import can_manage_members, can_view_members
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ProjectServiceError(ValueError):
    pass


class ProjectNotFound(ProjectServiceError):
    pass


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_projects(self, *, status: ProjectStatus | None = None) -> list[Project]:
        query = select(Project).order_by(Project.created_at.desc())
        if status is not None:
            query = query.where(Project.status == status)
        return list((await self.session.scalars(query)).all())

    async def get_project(self, project_id: UUID) -> Project:
        project = await self.session.get(Project, project_id)
        if project is None:
            raise ProjectNotFound("Project not found")
        return project

    async def create_project(
        self,
        *,
        actor: User,
        name: str,
        status: ProjectStatus,
        notes: str | None,
    ) -> Project:
        self._require_manage(actor)
        project = Project(name=name.strip(), status=status, notes=notes)
        if not project.name:
            raise ProjectServiceError("Project name cannot be empty")
        self.session.add(project)
        await self.session.flush()
        await AuditService(self.session).record(
            actor=actor,
            action="project.created",
            entity_type="project",
            entity_id=project.id,
            details={"name": project.name},
        )
        return project

    async def update_project(
        self,
        *,
        actor: User,
        project_id: UUID,
        name: str | None = None,
        status: ProjectStatus | None = None,
        notes: str | None = None,
    ) -> Project:
        self._require_manage(actor)
        project = await self.get_project(project_id)
        if name is not None:
            if not name.strip():
                raise ProjectServiceError("Project name cannot be empty")
            project.name = name.strip()
        if status is not None:
            project.status = status
        if notes is not None:
            project.notes = notes
        await self.session.flush()
        await AuditService(self.session).record(
            actor=actor,
            action="project.updated",
            entity_type="project",
            entity_id=project.id,
        )
        return project

    async def assign_member(
        self, *, actor: User, project_id: UUID, member_id: UUID
    ) -> ProjectMember:
        self._require_manage(actor)
        await self.get_project(project_id)
        member = await self.session.get(Member, member_id)
        if member is None:
            raise ProjectServiceError("Member not found")
        if member.employment_status != EmploymentStatus.ACTIVE or not member.is_active:
            raise ProjectServiceError("Only active members can be assigned to a project")
        existing = await self.session.scalar(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.member_id == member_id,
            )
        )
        if existing is not None:
            return existing
        assignment = ProjectMember(project_id=project_id, member_id=member_id)
        self.session.add(assignment)
        await self.session.flush()
        await AuditService(self.session).record(
            actor=actor,
            action="project.member_assigned",
            entity_type="project_member",
            entity_id=assignment.id,
            details={"project_id": str(project_id), "member_id": str(member_id)},
        )
        return assignment

    async def remove_member(self, *, actor: User, project_id: UUID, member_id: UUID) -> None:
        self._require_manage(actor)
        await self.get_project(project_id)
        assignment = await self.session.scalar(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.member_id == member_id,
            )
        )
        if assignment is not None:
            await self.session.delete(assignment)
            await self.session.flush()
            await AuditService(self.session).record(
                actor=actor,
                action="project.member_removed",
                entity_type="project_member",
                entity_id=assignment.id,
                details={"project_id": str(project_id), "member_id": str(member_id)},
            )

    async def project_members(self, project_id: UUID) -> list[Member]:
        await self.get_project(project_id)
        return list(
            (
                await self.session.scalars(
                    select(Member)
                    .join(ProjectMember, ProjectMember.member_id == Member.id)
                    .where(ProjectMember.project_id == project_id)
                    .order_by(Member.full_name)
                )
            ).all()
        )

    @staticmethod
    def _require_manage(actor: User) -> None:
        if not can_manage_members(actor):
            raise ProjectServiceError("Only super admin or owner can manage projects")


class FinanceServiceError(ValueError):
    pass


class FinanceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_transaction(
        self,
        *,
        actor: User,
        transaction_type: TransactionType,
        amount_uzs: int,
        transaction_date: date,
        project_id: UUID | None,
        category: str | None,
        note: str | None,
        idempotency_key: str | None,
    ) -> FinancialTransaction:
        if not can_manage_members(actor):
            raise FinanceServiceError("Only super admin or owner can manage transactions")
        transaction_type = TransactionType(transaction_type)
        if amount_uzs <= 0:
            raise FinanceServiceError("Transaction amount must be positive")
        if project_id is not None and await self.session.get(Project, project_id) is None:
            raise FinanceServiceError("Project not found")
        if idempotency_key is not None:
            existing = await self.session.scalar(
                select(FinancialTransaction).where(
                    FinancialTransaction.idempotency_key == idempotency_key
                )
            )
            if existing is not None:
                return existing
        transaction = FinancialTransaction(
            transaction_type=transaction_type,
            amount_uzs=amount_uzs,
            transaction_date=transaction_date,
            project_id=project_id,
            category=category,
            note=note,
            idempotency_key=idempotency_key,
        )
        self.session.add(transaction)
        await self.session.flush()
        await AuditService(self.session).record(
            actor=actor,
            action="transaction.created",
            entity_type="financial_transaction",
            entity_id=transaction.id,
            details={"transaction_type": transaction_type.value, "amount_uzs": amount_uzs},
        )
        return transaction

    async def list_transactions(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        project_id: UUID | None = None,
    ) -> list[FinancialTransaction]:
        filters = []
        if start_date is not None:
            filters.append(FinancialTransaction.transaction_date >= start_date)
        if end_date is not None:
            filters.append(FinancialTransaction.transaction_date <= end_date)
        if project_id is not None:
            filters.append(FinancialTransaction.project_id == project_id)
        return list(
            (
                await self.session.scalars(
                    select(FinancialTransaction)
                    .where(*filters)
                    .order_by(FinancialTransaction.transaction_date.desc())
                )
            ).all()
        )

    async def monthly_summary(self, *, year: int, month: int) -> dict[str, int]:
        from calendar import monthrange

        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        rows = await self.list_transactions(start_date=start_date, end_date=end_date)
        income = sum(
            row.amount_uzs for row in rows if row.transaction_type == TransactionType.PROJECT_INCOME
        )
        expenses = sum(
            row.amount_uzs
            for row in rows
            if row.transaction_type
            in {TransactionType.PROJECT_EXPENSE, TransactionType.GENERAL_EXPENSE}
        )
        return {
            "year": year,
            "month": month,
            "income_uzs": income,
            "expense_uzs": expenses,
            "net_cashflow_uzs": income - expenses,
        }

    @staticmethod
    def can_view(actor: User) -> bool:
        return can_view_members(actor)
