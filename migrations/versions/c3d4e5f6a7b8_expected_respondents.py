"""recurring poll expected respondents + cannot-attend option.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply this revision."""
    op.add_column("recurring_polls", sa.Column("expected_respondents", sa.String(), nullable=True))
    op.add_column("recurring_polls", sa.Column("expected_role_id", sa.Integer(), nullable=True))
    op.add_column(
        "recurring_polls",
        sa.Column("allow_cannot_attend", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("recurring_polls", sa.Column("last_reminded_week", sa.String(), nullable=True))


def downgrade() -> None:
    """Revert this revision."""
    op.drop_column("recurring_polls", "last_reminded_week")
    op.drop_column("recurring_polls", "allow_cannot_attend")
    op.drop_column("recurring_polls", "expected_role_id")
    op.drop_column("recurring_polls", "expected_respondents")
