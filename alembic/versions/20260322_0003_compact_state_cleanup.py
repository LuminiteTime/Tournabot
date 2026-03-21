"""Clean existing DB before switching to compact tournament state."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260322_0003"
down_revision = "20260314_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    tables_to_clean = [
        table_name
        for table_name in ("bug_reports", "tournaments")
        if insp.has_table(table_name)
    ]
    if not tables_to_clean:
        return

    quoted_tables = ", ".join(f'"{table_name}"' for table_name in tables_to_clean)
    op.execute(sa.text(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY"))


def downgrade() -> None:
    # Данные удалены безвозвратно; восстанавливать нечего.
    return
