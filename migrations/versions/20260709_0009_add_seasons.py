"""add_seasons

Revision ID: 20260709_0009
Revises: 20260709_0008
Create Date: 2026-07-09 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '20260709_0009'
down_revision: str | None = '20260709_0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # seasons table
    op.create_table(
        'seasons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_seasons'))
    )
    op.create_index('ix_seasons_is_active', 'seasons', ['is_active'], unique=False)

    # user_season_history table
    op.create_table(
        'user_season_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('final_xp', sa.Integer(), nullable=False),
        sa.Column('final_level', sa.Integer(), nullable=False),
        sa.Column('final_rank', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], name=op.f('fk_user_season_history_season_id_seasons')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_season_history_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_season_history'))
    )
    op.create_index('ix_user_season_history_season_id', 'user_season_history', ['season_id'], unique=False)
    op.create_index('ix_user_season_history_user_id', 'user_season_history', ['user_id'], unique=False)
    op.create_index('ux_user_season', 'user_season_history', ['user_id', 'season_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ux_user_season', table_name='user_season_history')
    op.drop_index('ix_user_season_history_user_id', table_name='user_season_history')
    op.drop_index('ix_user_season_history_season_id', table_name='user_season_history')
    op.drop_table('user_season_history')
    op.drop_index('ix_seasons_is_active', table_name='seasons')
    op.drop_table('seasons')
