"""add append-only audit logs for Phase 6"""

from alembic import op
from sqlalchemy import MetaData

revision = "0005_audit_logs"
down_revision = "0004_payroll_and_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.models.entities import Base

    metadata = MetaData()
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, "audit_logs"):
        Base.metadata.tables["users"].to_metadata(metadata)
        Base.metadata.tables["audit_logs"].to_metadata(metadata)
    metadata.create_all(bind)


def downgrade() -> None:
    from app.models.entities import Base

    bind = op.get_bind()
    if bind.dialect.has_table(bind, "audit_logs"):
        Base.metadata.tables["audit_logs"].drop(bind)
