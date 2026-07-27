"""initial polls table

Revision ID: 7c2503d73cf3
Revises: 
Create Date: 2026-05-24 23:07:24.124076

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c2503d73cf3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS polls (
            msg_id INTEGER NOT NULL PRIMARY KEY,
            data VARCHAR NOT NULL
        )
    """)


def downgrade() -> None:
    op.drop_table('polls')
