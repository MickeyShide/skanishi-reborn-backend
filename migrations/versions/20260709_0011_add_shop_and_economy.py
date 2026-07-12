"""add_shop_and_economy

Revision ID: 20260709_0011
Revises: 20260709_0010
Create Date: 2026-07-09 00:15:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260709_0011'
down_revision: str | None = '20260709_0010'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create shop_items table
    op.create_table('shop_items',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('item_type', sa.String(length=64), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('asset_url', sa.String(length=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_shop_items'))
    )
    
    # 2. Add economy & cosmetic fields to users
    op.add_column('users', sa.Column('coins', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('active_border_id', sa.BigInteger(), nullable=True))
    op.add_column('users', sa.Column('active_bg_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(op.f('fk_users_active_border_id_shop_items'), 'users', 'shop_items', ['active_border_id'], ['id'])
    op.create_foreign_key(op.f('fk_users_active_bg_id_shop_items'), 'users', 'shop_items', ['active_bg_id'], ['id'])
    
    # 3. Create user_cosmetics table
    op.create_table('user_cosmetics',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('shop_item_id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['shop_item_id'], ['shop_items.id'], name=op.f('fk_user_cosmetics_shop_item_id_shop_items')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_cosmetics_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_cosmetics')),
        sa.UniqueConstraint('user_id', 'shop_item_id', name='uq_user_shop_item')
    )


def downgrade() -> None:
    op.drop_table('user_cosmetics')
    op.drop_constraint(op.f('fk_users_active_bg_id_shop_items'), 'users', type_='foreignkey')
    op.drop_constraint(op.f('fk_users_active_border_id_shop_items'), 'users', type_='foreignkey')
    op.drop_column('users', 'active_bg_id')
    op.drop_column('users', 'active_border_id')
    op.drop_column('users', 'coins')
    op.drop_table('shop_items')
