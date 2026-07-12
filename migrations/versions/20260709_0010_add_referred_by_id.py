"""add_referred_by_id

Revision ID: 20260709_0010
Revises: 20260709_0009
Create Date: 2026-07-09 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260709_0010'
down_revision: str | None = '20260709_0009'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('referred_by_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(op.f('fk_users_referred_by_id_users'), 'users', 'users', ['referred_by_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint(op.f('fk_users_referred_by_id_users'), 'users', type_='foreignkey')
    op.drop_column('users', 'referred_by_id')
