"""add Phase 2 member and salary fields"""

import sqlalchemy as sa
from alembic import op

revision = "0002_members_and_salary_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {item["name"] for item in inspector.get_columns(table)}
    if column.name not in existing:
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing("members", sa.Column("role", sa.String(20), nullable=True))
    _add_column_if_missing("members", sa.Column("phone_number", sa.String(30), nullable=True))
    _add_column_if_missing("members", sa.Column("telegram_user_id", sa.BigInteger(), nullable=True))
    _add_column_if_missing("members", sa.Column("employment_status", sa.String(20), nullable=True))
    _add_column_if_missing("members", sa.Column("joined_on", sa.Date(), nullable=True))
    _add_column_if_missing("members", sa.Column("ended_on", sa.Date(), nullable=True))
    _add_column_if_missing("members", sa.Column("notes", sa.Text(), nullable=True))
    _add_column_if_missing(
        "salary_history", sa.Column("created_by_user_id", sa.Uuid(), nullable=True)
    )

    op.execute("UPDATE members SET role = member_type WHERE role IS NULL")
    op.execute("UPDATE members SET employment_status = 'ACTIVE' WHERE employment_status IS NULL")
    op.execute("UPDATE members SET joined_on = CURRENT_DATE WHERE joined_on IS NULL")

    op.create_index("ix_members_role", "members", ["role"], unique=False, if_not_exists=True)
    op.create_index(
        "ix_members_employment_status",
        "members",
        ["employment_status"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_members_telegram_user_id",
        "members",
        ["telegram_user_id"],
        unique=True,
        if_not_exists=True,
    )
    op.create_index(
        "ix_salary_history_created_by_user_id",
        "salary_history",
        ["created_by_user_id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_salary_history_created_by_user_id", table_name="salary_history", if_exists=True
    )
    op.drop_index("ix_members_telegram_user_id", table_name="members", if_exists=True)
    op.drop_index("ix_members_employment_status", table_name="members", if_exists=True)
    op.drop_index("ix_members_role", table_name="members", if_exists=True)
    for table, column in (
        ("salary_history", "created_by_user_id"),
        ("members", "notes"),
        ("members", "ended_on"),
        ("members", "joined_on"),
        ("members", "employment_status"),
        ("members", "telegram_user_id"),
        ("members", "phone_number"),
        ("members", "role"),
    ):
        inspector = sa.inspect(op.get_bind())
        if column in {item["name"] for item in inspector.get_columns(table)}:
            op.drop_column(table, column)
