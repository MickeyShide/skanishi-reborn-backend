"""add_cooldown_to_item_secrets

Revision ID: 20260712_0012
Revises: 20260709_0011
Create Date: 2026-07-12 11:10:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260712_0012'
down_revision: str | None = '20260709_0011'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column('item_secrets', sa.Column('validation_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('item_secrets', sa.Column('cooldown_until', sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column('item_secrets', 'cooldown_until')
    op.drop_column('item_secrets', 'validation_count')
