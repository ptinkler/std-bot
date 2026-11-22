"""store allow_cannot_attend as a boolean.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Declare the column as BOOLEAN; SQLite stores it as 0/1 either way, so no value changes."""
    with op.batch_alter_table("recurring_polls") as batch:
        batch.alter_column(
            "allow_cannot_attend",
            existing_type=sa.Integer(),
            type_=sa.Boolean(),
            existing_nullable=False,
            existing_server_default=sa.text("1"),
        )


def downgrade() -> None:
    """Declare the column as INTEGER again."""
    with op.batch_alter_table("recurring_polls") as batch:
        batch.alter_column(
            "allow_cannot_attend",
            existing_type=sa.Boolean(),
            type_=sa.Integer(),
            existing_nullable=False,
            existing_server_default=sa.text("1"),
        )
