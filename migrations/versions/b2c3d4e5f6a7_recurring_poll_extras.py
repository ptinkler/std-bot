"""recurring poll extras: last_poll_msg_id, mention_role_id.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-26 00:01:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply this revision."""
    op.add_column("recurring_polls", sa.Column("last_poll_msg_id", sa.Integer(), nullable=True))
    op.add_column("recurring_polls", sa.Column("mention_role_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Revert this revision."""
    op.drop_column("recurring_polls", "mention_role_id")
    op.drop_column("recurring_polls", "last_poll_msg_id")
