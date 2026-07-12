"""add_fragments_and_crafting

Revision ID: 20260712_0013
Revises: 20260712_0012
Create Date: 2026-07-12 11:15:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260712_0013'
down_revision: str | None = '20260712_0012'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    # Add fragments to users
    op.add_column('users', sa.Column('fragments_common', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('fragments_rare', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('fragments_epic', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('fragments_legendary', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('fragments_mythic', sa.Integer(), server_default='0', nullable=False))
    
    # Add fragment crafting logic to shop_items
    op.add_column('shop_items', sa.Column('fragment_cost', sa.Integer(), nullable=True))
    op.add_column('shop_items', sa.Column('fragment_rarity', sa.String(length=32), nullable=True))

def downgrade() -> None:
    op.drop_column('shop_items', 'fragment_rarity')
    op.drop_column('shop_items', 'fragment_cost')
    
    op.drop_column('users', 'fragments_mythic')
    op.drop_column('users', 'fragments_legendary')
    op.drop_column('users', 'fragments_epic')
    op.drop_column('users', 'fragments_rare')
    op.drop_column('users', 'fragments_common')
