"""ensure project and finance tables exist for Phase 4"""

from alembic import op
from sqlalchemy import MetaData

revision = "0003_projects_and_finance"
down_revision = "0002_members_and_salary_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.models.entities import Base

    metadata = MetaData()
    bind = op.get_bind()
    for table_name in (
        "projects",
        "project_members",
        "financial_transactions",
    ):
        if not bind.dialect.has_table(bind, table_name):
            Base.metadata.tables[table_name].to_metadata(metadata)
    metadata.create_all(bind)


def downgrade() -> None:
    from app.models.entities import Base

    bind = op.get_bind()
    for table_name in (
        "financial_transactions",
        "project_members",
        "projects",
    ):
        if bind.dialect.has_table(bind, table_name):
            Base.metadata.tables[table_name].drop(bind)
