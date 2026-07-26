"""add recurring polls table

Revision ID: a1b2c3d4e5f6
Revises: 7c2503d73cf3
Create Date: 2026-07-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7c2503d73cf3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'recurring_polls',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('event_name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('creator_id', sa.Integer(), nullable=False),
        sa.Column('guild_id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=False),
        sa.Column('post_weekday', sa.Integer(), nullable=False),
        sa.Column('post_hour', sa.Integer(), nullable=False),
        sa.Column('post_minute', sa.Integer(), nullable=False),
        sa.Column('post_timezone', sa.String(), nullable=False),
        sa.Column('last_posted_week', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('recurring_polls')
