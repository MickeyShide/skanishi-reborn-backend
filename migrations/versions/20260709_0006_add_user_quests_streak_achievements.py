"""Add user_quests, streak fields, daily fields, achievement_conditions

Revision ID: 20260709_0006
Revises: 20260706_0005
Create Date: 2026-07-09 00:00:00.000000

Changes:
  1. users: add last_login_at, last_daily_claimed_at, streak_last_date
  2. user_quests: per-user quest progress table
  3. achievement_conditions: typed conditions for auto-unlock
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260709_0006"
down_revision: str | Sequence[str] | None = "20260706_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────
    # 1. Add streak / daily login fields to users
    # ──────────────────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "last_login_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="UTC timestamp of the most recent successful app_state fetch",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "last_daily_claimed_at",
            sa.Date(),
            nullable=True,
            comment="UTC calendar date when the daily reward was last claimed",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "streak_last_date",
            sa.Date(),
            nullable=True,
            comment="UTC calendar date of the last login that counted toward the streak",
        ),
    )

    op.create_index("ix_users_last_login_at", "users", ["last_login_at"])

    # ──────────────────────────────────────────────────────────
    # 2. Create user_quests (per-user quest progress)
    # ──────────────────────────────────────────────────────────
    op.create_table(
        "user_quests",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("quest_id", sa.String(96), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "reward_claimed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.current_timestamp(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_user_quests_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["quest_id"],
            ["quests.id"],
            ondelete="CASCADE",
            name="fk_user_quests_quest_id_quests",
        ),
        sa.UniqueConstraint("user_id", "quest_id", name="ux_user_quests_user_quest"),
        sa.CheckConstraint("progress >= 0", name="ck_user_quests_progress_non_negative"),
    )
    op.create_index("ix_user_quests_user_id", "user_quests", ["user_id"])
    op.create_index("ix_user_quests_quest_id", "user_quests", ["quest_id"])
    op.create_index(
        "ix_user_quests_completed",
        "user_quests",
        ["user_id", "completed_at"],
    )

    # ──────────────────────────────────────────────────────────
    # 3. Create achievement_conditions
    # ──────────────────────────────────────────────────────────
    achievement_condition_type = postgresql.ENUM(
        "scan_count",
        "xp_total",
        "level_reached",
        "collection_complete",
        "streak_days",
        "quest_count",
        name="achievementconditiontype",
        create_type=False,
    )
    op.execute("DROP TYPE IF EXISTS achievementconditiontype CASCADE")
    op.execute("CREATE TYPE achievementconditiontype AS ENUM ('scan_count', 'xp_total', 'level_reached', 'collection_complete', 'streak_days', 'quest_count')")

    op.create_table(
        "achievement_conditions",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("achievement_id", sa.String(96), nullable=False),
        sa.Column(
            "condition_type",
            achievement_condition_type,
            nullable=False,
        ),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.current_timestamp(),
        ),
        sa.ForeignKeyConstraint(
            ["achievement_id"],
            ["achievements.id"],
            ondelete="CASCADE",
            name="fk_achievement_conditions_achievement_id",
        ),
        sa.CheckConstraint(
            "threshold > 0",
            name="ck_achievement_conditions_threshold_positive",
        ),
    )
    op.create_index(
        "ix_achievement_conditions_achievement_id",
        "achievement_conditions",
        ["achievement_id"],
    )


def downgrade() -> None:
    op.drop_table("achievement_conditions")
    postgresql.ENUM(name="achievementconditiontype").drop(op.get_bind(), checkfirst=True)

    op.drop_table("user_quests")

    op.drop_index("ix_users_last_login_at", table_name="users")
    op.drop_column("users", "streak_last_date")
    op.drop_column("users", "last_daily_claimed_at")
    op.drop_column("users", "last_login_at")
