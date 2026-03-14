"""Add reporter_alias to bug_reports."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260314_0002"
down_revision = "20260314_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("bug_reports"):
        return

    cols = {c["name"] for c in insp.get_columns("bug_reports")}
    if "reporter_alias" not in cols:
        op.add_column("bug_reports", sa.Column("reporter_alias", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("bug_reports"):
        return

    cols = {c["name"] for c in insp.get_columns("bug_reports")}
    if "reporter_alias" in cols:
        op.drop_column("bug_reports", "reporter_alias")

