"""Initial schema (tournaments, bug_reports).

This migration is written to be safe on an existing DB that might already
have been initialized via SQLAlchemy `create_all()` (pre-migrations era).
If tables already exist, it will not attempt to recreate them.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260314_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("tournaments"):
        op.create_table(
            "tournaments",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("chat_id", sa.BigInteger(), nullable=False),
            sa.Column("message_id", sa.BigInteger(), nullable=True),
            sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("chat_id", name="uq_tournaments_chat_id"),
        )
        op.create_index("ix_tournaments_chat_id", "tournaments", ["chat_id"], unique=False)

    if not insp.has_table("bug_reports"):
        op.create_table(
            "bug_reports",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("reporter_chat_id", sa.BigInteger(), nullable=False),
            sa.Column("reporter_user_id", sa.BigInteger(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_bug_reports_reporter_chat_id", "bug_reports", ["reporter_chat_id"], unique=False)
        op.create_index("ix_bug_reports_reporter_user_id", "bug_reports", ["reporter_user_id"], unique=False)
        op.create_index("ix_bug_reports_is_done", "bug_reports", ["is_done"], unique=False)
        op.create_index("ix_bug_reports_created_at", "bug_reports", ["created_at"], unique=False)


def downgrade() -> None:
    # Downgrade intentionally drops tables (safe because this is the initial migration).
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("bug_reports"):
        op.drop_index("ix_bug_reports_created_at", table_name="bug_reports")
        op.drop_index("ix_bug_reports_is_done", table_name="bug_reports")
        op.drop_index("ix_bug_reports_reporter_user_id", table_name="bug_reports")
        op.drop_index("ix_bug_reports_reporter_chat_id", table_name="bug_reports")
        op.drop_table("bug_reports")

    if insp.has_table("tournaments"):
        op.drop_index("ix_tournaments_chat_id", table_name="tournaments")
        op.drop_table("tournaments")

