"""initial polls table.

Revision ID: 7c2503d73cf3
Revises:
Create Date: 2026-05-24 23:07:24.124076

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c2503d73cf3"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply this revision."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS polls (
            msg_id INTEGER NOT NULL PRIMARY KEY,
            data VARCHAR NOT NULL
        )
    """)


def downgrade() -> None:
    """Revert this revision."""
    op.drop_table("polls")
