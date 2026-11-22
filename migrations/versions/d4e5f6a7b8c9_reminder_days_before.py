"""recurring poll configurable reminder lead time.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-25 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply this revision."""
    op.add_column(
        "recurring_polls",
        sa.Column("reminder_days_before", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    """Revert this revision."""
    op.drop_column("recurring_polls", "reminder_days_before")
