"""Add target_count and condition_tag to quests

Revision ID: 20260709_0008
Revises: 20260709_0007
Create Date: 2026-07-09 00:02:00.000000

Changes:
  1. quests: add target_count (INT, default 1)
  2. quests: add condition_tag (VARCHAR 64, nullable)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260709_0008"
down_revision: str | Sequence[str] | None = "20260709_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "quests",
        sa.Column(
            "target_count",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Number of qualifying actions required to complete this quest",
        ),
    )
    op.add_column(
        "quests",
        sa.Column(
            "condition_tag",
            sa.String(64),
            nullable=True,
            comment="Optional XpEvent tag that qualifying scans must carry",
        ),
    )
    op.create_check_constraint(
        "ck_quests_target_count_positive",
        "quests",
        "target_count > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_quests_target_count_positive", "quests", type_="check")
    op.drop_column("quests", "condition_tag")
    op.drop_column("quests", "target_count")
