from datetime import date, timedelta
from uuid import UUID

from app.models.entities import EmploymentStatus, Member, MemberType, Role, SalaryHistory, User
from app.services.authorization import require_member_management
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


class MemberServiceError(ValueError):
    pass


class MemberNotFound(MemberServiceError):
    pass


class SalaryPeriodOverlap(MemberServiceError):
    pass


class MemberService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_members(
        self,
        *,
        role: Role | None,
        active: bool | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Member], int]:
        filters = []
        if role is not None:
            filters.append(Member.role == role)
        if active is not None:
            filters.append(
                Member.employment_status
                == (EmploymentStatus.ACTIVE if active else EmploymentStatus.INACTIVE)
            )
        total = await self.session.scalar(select(func.count(Member.id)).where(*filters))
        members = list(
            (
                await self.session.scalars(
                    select(Member)
                    .where(*filters)
                    .order_by(Member.full_name)
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        )
        return members, int(total or 0)

    async def get_member(self, member_id: UUID) -> Member:
        member = await self.session.get(Member, member_id)
        if member is None:
            raise MemberNotFound("Member not found")
        return member

    async def user_by_telegram_id(self, telegram_user_id: int) -> User | None:
        return await self.session.scalar(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )

    async def create_member(
        self,
        *,
        actor: User,
        full_name: str,
        role: Role,
        phone_number: str | None,
        telegram_user_id: int | None,
        employment_status: EmploymentStatus,
        joined_on: date,
        ended_on: date | None,
        notes: str | None,
    ) -> Member:
        require_member_management(actor)
        self._validate_dates(joined_on, ended_on)
        if telegram_user_id is not None:
            await self._ensure_telegram_id_available(telegram_user_id)
        member = Member(
            full_name=full_name,
            member_type=MemberType(role.value),
            role=role,
            phone_number=phone_number,
            telegram_user_id=telegram_user_id,
            employment_status=employment_status,
            joined_on=joined_on,
            ended_on=ended_on,
            notes=notes,
        )
        if telegram_user_id is not None:
            member.user_id = await self._link_user(telegram_user_id, role)
        self.session.add(member)
        await self.session.flush()
        return member

    async def update_member(self, *, actor: User, member_id: UUID, **changes: object) -> Member:
        require_member_management(actor)
        member = await self.get_member(member_id)
        raw_role = changes.get("role")
        role = member.role if raw_role is None else Role(raw_role)
        telegram_user_id = changes.get("telegram_user_id", member.telegram_user_id)
        joined_on = changes.get("joined_on") or member.joined_on
        ended_on = changes.get("ended_on", member.ended_on)
        if not isinstance(joined_on, date) or not isinstance(ended_on, (date, type(None))):
            raise MemberServiceError("Invalid member update")
        self._validate_dates(joined_on, ended_on)
        if role != Role.WORKER and member.role == Role.WORKER:
            has_salary = await self.session.scalar(
                select(SalaryHistory.id).where(SalaryHistory.member_id == member.id).limit(1)
            )
            if has_salary is not None:
                raise MemberServiceError(
                    "A worker with salary history cannot become an owner or partner"
                )
        raw_status = changes.get("employment_status")
        employment_status = (
            member.employment_status if raw_status is None else EmploymentStatus(raw_status)
        )
        if telegram_user_id != member.telegram_user_id and telegram_user_id is not None:
            if not isinstance(telegram_user_id, int):
                raise MemberServiceError("Invalid Telegram user ID")
            await self._ensure_telegram_id_available(telegram_user_id, member.id)
            member.user_id = await self._link_user(telegram_user_id, role)
        member.full_name = str(changes.get("full_name", member.full_name))
        member.role = role
        member.member_type = MemberType(role.value)
        member.phone_number = changes.get("phone_number", member.phone_number)  # type: ignore[assignment]
        member.telegram_user_id = telegram_user_id  # type: ignore[assignment]
        member.employment_status = employment_status
        member.joined_on = joined_on
        member.ended_on = ended_on
        member.notes = changes.get("notes", member.notes)  # type: ignore[assignment]
        if telegram_user_id is None:
            member.user_id = None
        await self.session.flush()
        return member

    async def deactivate_member(
        self,
        *,
        actor: User,
        member_id: UUID,
        ended_on: date | None,
    ) -> Member:
        require_member_management(actor)
        member = await self.get_member(member_id)
        end_date = ended_on or date.today()
        if end_date < member.joined_on:
            raise MemberServiceError("End date cannot be before join date")
        member.employment_status = EmploymentStatus.INACTIVE
        member.is_active = False
        member.ended_on = end_date
        await self.session.flush()
        return member

    async def link_telegram(self, *, actor: User, member_id: UUID, telegram_user_id: int) -> Member:
        require_member_management(actor)
        member = await self.get_member(member_id)
        await self._ensure_telegram_id_available(telegram_user_id, member.id)
        member.telegram_user_id = telegram_user_id
        member.user_id = await self._link_user(telegram_user_id, member.role)
        await self.session.flush()
        return member

    async def unlink_telegram(self, *, actor: User, member_id: UUID) -> Member:
        require_member_management(actor)
        member = await self.get_member(member_id)
        member.telegram_user_id = None
        member.user_id = None
        await self.session.flush()
        return member

    async def create_salary(
        self,
        *,
        actor: User,
        member_id: UUID,
        monthly_salary_uzs: int,
        effective_from: date,
        effective_to: date | None,
    ) -> SalaryHistory:
        require_member_management(actor)
        member = await self.get_member(member_id)
        if member.role != Role.WORKER:
            raise MemberServiceError("Only workers can receive a fixed salary")
        if monthly_salary_uzs < 0:
            raise MemberServiceError("Salary cannot be negative")
        self._validate_dates(effective_from, effective_to)
        overlapping_periods = list(
            (
                await self.session.scalars(
                    select(SalaryHistory).where(
                        SalaryHistory.member_id == member_id,
                        SalaryHistory.effective_from <= (effective_to or date.max),
                        or_(
                            SalaryHistory.effective_to.is_(None),
                            SalaryHistory.effective_to >= effective_from,
                        ),
                    )
                )
            ).all()
        )
        for period in overlapping_periods:
            if period.effective_from < effective_from and period.effective_to is None:
                period.effective_to = effective_from - timedelta(days=1)
            else:
                raise SalaryPeriodOverlap("Salary periods cannot overlap")
        salary = SalaryHistory(
            member_id=member_id,
            monthly_salary_uzs=monthly_salary_uzs,
            effective_from=effective_from,
            effective_to=effective_to,
            created_by_user_id=actor.id,
        )
        self.session.add(salary)
        await self.session.flush()
        return salary

    async def salary_history(self, member_id: UUID) -> list[SalaryHistory]:
        await self.get_member(member_id)
        return list(
            (
                await self.session.scalars(
                    select(SalaryHistory)
                    .where(SalaryHistory.member_id == member_id)
                    .order_by(SalaryHistory.effective_from.desc())
                )
            ).all()
        )

    async def _ensure_telegram_id_available(
        self,
        telegram_user_id: int,
        member_id: UUID | None = None,
    ) -> None:
        query = select(Member).where(Member.telegram_user_id == telegram_user_id)
        if member_id is not None:
            query = query.where(Member.id != member_id)
        if await self.session.scalar(query) is not None:
            raise MemberServiceError("Telegram account is already linked to another member")

    async def _link_user(self, telegram_user_id: int, role: Role) -> UUID:
        user = await self.session.scalar(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        if user is None:
            user = User(telegram_user_id=telegram_user_id, role=role)
            self.session.add(user)
            await self.session.flush()
        else:
            user.role = role
            user.is_active = True
        return user.id

    @staticmethod
    def _validate_dates(start: date, end: date | None) -> None:
        if end is not None and end < start:
            raise MemberServiceError("End date cannot be before start date")
