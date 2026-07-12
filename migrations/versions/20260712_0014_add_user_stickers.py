"""add_user_stickers

Revision ID: 20260712_0014
Revises: 20260712_0013
Create Date: 2026-07-12 11:21:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260712_0014'
down_revision: str | None = '20260712_0013'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table(
        'user_stickers',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('scan_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_passive_xp', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_passive_coins', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_stickers_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_user_stickers'),
        sa.UniqueConstraint('user_id', name='uq_user_stickers_user_id')
    )
    op.create_index('ux_user_stickers_token', 'user_stickers', ['token'], unique=True)
    
    op.create_table(
        'user_sticker_scans',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('sticker_id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['sticker_id'], ['user_stickers.id'], name='fk_user_sticker_scans_sticker_id_user_stickers', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_sticker_scans_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_user_sticker_scans'),
        sa.UniqueConstraint('user_id', 'sticker_id', name='ux_user_sticker_scans_user_sticker')
    )
    op.create_index('ix_user_sticker_scans_sticker_id', 'user_sticker_scans', ['sticker_id'], unique=False)

def downgrade() -> None:
    op.drop_table('user_sticker_scans')
    op.drop_table('user_stickers')
