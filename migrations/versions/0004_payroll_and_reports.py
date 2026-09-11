"""ensure payroll tables exist for Phase 5"""

from alembic import op
from sqlalchemy import MetaData

revision = "0004_payroll_and_reports"
down_revision = "0003_projects_and_finance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.models.entities import Base

    metadata = MetaData()
    bind = op.get_bind()
    for table_name in ("monthly_payroll", "payroll_payments", "profit_distributions"):
        if not bind.dialect.has_table(bind, table_name):
            Base.metadata.tables[table_name].to_metadata(metadata)
    metadata.create_all(bind)


def downgrade() -> None:
    from app.models.entities import Base

    bind = op.get_bind()
    for table_name in ("payroll_payments", "monthly_payroll", "profit_distributions"):
        if bind.dialect.has_table(bind, table_name):
            Base.metadata.tables[table_name].drop(bind)
