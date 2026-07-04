"""add skanshi ui models

Revision ID: 20260704_0004
Revises: 20260704_0003
Create Date: 2026-07-04 00:04:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260704_0004"
down_revision: str | Sequence[str] | None = "20260704_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def id_column() -> sa.Column:
    return sa.Column(
        "id",
        sa.BigInteger(),
        sa.Identity(always=False),
        primary_key=True,
        nullable=False,
    )


def slug_id_column() -> sa.Column:
    return sa.Column(
        "id",
        sa.String(length=96),
        primary_key=True,
        nullable=False,
    )


def rarity_enum() -> postgresql.ENUM:
    return postgresql.ENUM(
        "common",
        "rare",
        "epic",
        "legendary",
        "mythic",
        name="rarity",
        create_type=False,
    )


def ui_color_token_enum() -> postgresql.ENUM:
    return postgresql.ENUM(
        "cyan",
        "violetHi",
        "gold",
        "pink",
        name="ui_color_token",
        create_type=False,
    )


def upgrade() -> None:
    rarity = rarity_enum()
    ui_color_token = ui_color_token_enum()
    bind = op.get_bind()

    rarity.create(bind, checkfirst=True)
    ui_color_token.create(bind, checkfirst=True)

    op.add_column(
        "users",
        sa.Column("display_name", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("public_id", sa.String(length=64), nullable=True),
    )
    op.add_column("users", sa.Column("rank", sa.Integer(), nullable=True))
    op.add_column(
        "users",
        sa.Column("level", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column(
            "level_progress",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("xp", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column(
            "next_level_xp",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "streak_days",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("season_label", sa.String(length=160), nullable=True),
    )
    op.create_check_constraint(
        "ck_users_rank_positive_or_null",
        "users",
        "rank IS NULL OR rank > 0",
    )
    op.create_check_constraint(
        "ck_users_level_positive",
        "users",
        "level > 0",
    )
    op.create_check_constraint(
        "ck_users_level_progress_range",
        "users",
        "level_progress BETWEEN 0 AND 100",
    )
    op.create_check_constraint(
        "ck_users_xp_non_negative",
        "users",
        "xp >= 0",
    )
    op.create_check_constraint(
        "ck_users_next_level_xp_non_negative",
        "users",
        "next_level_xp >= 0",
    )
    op.create_check_constraint(
        "ck_users_streak_days_non_negative",
        "users",
        "streak_days >= 0",
    )
    op.create_index("ix_users_rank", "users", ["rank"])
    op.create_index(
        "ux_users_public_id_not_null",
        "users",
        ["public_id"],
        unique=True,
        postgresql_where=sa.text("public_id IS NOT NULL"),
    )

    op.create_table(
        "quests",
        slug_id_column(),
        *timestamps(),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("step_label", sa.String(length=80), nullable=False),
        sa.Column(
            "progress_percent",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("rarity", rarity, nullable=False),
        sa.Column(
            "reward_xp",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("season_id", sa.String(length=96), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "progress_percent BETWEEN 0 AND 100",
            name="ck_quests_progress_percent_range",
        ),
        sa.CheckConstraint(
            "reward_xp >= 0",
            name="ck_quests_reward_xp_non_negative",
        ),
    )
    op.create_index("ix_quests_active", "quests", ["is_active"])
    op.create_index("ix_quests_rarity", "quests", ["rarity"])
    op.create_index("ix_quests_season_id", "quests", ["season_id"])

    op.create_table(
        "events",
        slug_id_column(),
        *timestamps(),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("rarity", rarity, nullable=False),
        sa.Column(
            "xp_multiplier",
            sa.Numeric(5, 2),
            server_default="1",
            nullable=False,
        ),
        sa.Column("starts_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ends_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "xp_multiplier > 0",
            name="ck_events_xp_multiplier_positive",
        ),
        sa.CheckConstraint("ends_at > starts_at", name="ck_events_period_valid"),
    )
    op.create_index("ix_events_active", "events", ["is_active"])
    op.create_index(
        "ix_events_active_ends_at",
        "events",
        ["is_active", "ends_at"],
    )
    op.create_index("ix_events_rarity", "events", ["rarity"])

    op.create_table(
        "achievements",
        slug_id_column(),
        *timestamps(),
        sa.Column("icon", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("rarity", rarity, nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "reward_xp",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.CheckConstraint(
            "reward_xp >= 0",
            name="ck_achievements_reward_xp_non_negative",
        ),
    )
    op.create_index("ix_achievements_rarity", "achievements", ["rarity"])

    op.create_table(
        "map_points",
        slug_id_column(),
        *timestamps(),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("rarity", rarity, nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column(
            "reward_xp",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("quest_id", sa.String(length=96), nullable=True),
        sa.Column(
            "is_big",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "has_hint",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "latitude BETWEEN -90 AND 90",
            name="ck_map_points_latitude_range",
        ),
        sa.CheckConstraint(
            "longitude BETWEEN -180 AND 180",
            name="ck_map_points_longitude_range",
        ),
        sa.CheckConstraint(
            "reward_xp >= 0",
            name="ck_map_points_reward_xp_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["quest_id"],
            ["quests.id"],
            name="fk_map_points_quest_id_quests",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_map_points_active", "map_points", ["is_active"])
    op.create_index("ix_map_points_rarity", "map_points", ["rarity"])
    op.create_index(
        "ix_map_points_lat_lon",
        "map_points",
        ["latitude", "longitude"],
    )
    op.create_index("ix_map_points_quest_id", "map_points", ["quest_id"])

    op.create_table(
        "xp_events",
        id_column(),
        *timestamps(),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=180), nullable=False),
        sa.Column("tag", sa.String(length=32), nullable=True),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("multiplier", sa.Numeric(5, 2), nullable=True),
        sa.Column("color", ui_color_token, nullable=True),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint(
            "multiplier IS NULL OR multiplier > 0",
            name="ck_xp_events_multiplier_positive_or_null",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_xp_events_user_id_users",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_xp_events_user_occurred",
        "xp_events",
        ["user_id", sa.text("occurred_at DESC")],
    )

    op.create_table(
        "user_achievements",
        id_column(),
        *timestamps(),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("achievement_id", sa.String(length=96), nullable=False),
        sa.Column(
            "unlocked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "progress_percent",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("unlocked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "progress_percent BETWEEN 0 AND 100",
            name="ck_user_achievements_progress_percent_range",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_achievements_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["achievement_id"],
            ["achievements.id"],
            name="fk_user_achievements_achievement_id_achievements",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ux_user_achievements_user_achievement",
        "user_achievements",
        ["user_id", "achievement_id"],
        unique=True,
    )
    op.create_index(
        "ix_user_achievements_user_id",
        "user_achievements",
        ["user_id"],
    )
    op.create_index(
        "ix_user_achievements_achievement_id",
        "user_achievements",
        ["achievement_id"],
    )
    op.create_index(
        "ix_user_achievements_unlocked",
        "user_achievements",
        ["unlocked"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_achievements_unlocked", table_name="user_achievements")
    op.drop_index(
        "ix_user_achievements_achievement_id",
        table_name="user_achievements",
    )
    op.drop_index("ix_user_achievements_user_id", table_name="user_achievements")
    op.drop_index(
        "ux_user_achievements_user_achievement",
        table_name="user_achievements",
    )
    op.drop_table("user_achievements")

    op.drop_index("ix_xp_events_user_occurred", table_name="xp_events")
    op.drop_table("xp_events")

    op.drop_index("ix_map_points_quest_id", table_name="map_points")
    op.drop_index("ix_map_points_lat_lon", table_name="map_points")
    op.drop_index("ix_map_points_rarity", table_name="map_points")
    op.drop_index("ix_map_points_active", table_name="map_points")
    op.drop_table("map_points")

    op.drop_index("ix_achievements_rarity", table_name="achievements")
    op.drop_table("achievements")

    op.drop_index("ix_events_rarity", table_name="events")
    op.drop_index("ix_events_active_ends_at", table_name="events")
    op.drop_index("ix_events_active", table_name="events")
    op.drop_table("events")

    op.drop_index("ix_quests_season_id", table_name="quests")
    op.drop_index("ix_quests_rarity", table_name="quests")
    op.drop_index("ix_quests_active", table_name="quests")
    op.drop_table("quests")

    ui_color_token_enum().drop(op.get_bind(), checkfirst=True)
    rarity_enum().drop(op.get_bind(), checkfirst=True)

    op.drop_index("ux_users_public_id_not_null", table_name="users")
    op.drop_index("ix_users_rank", table_name="users")
    op.drop_constraint(
        "ck_users_streak_days_non_negative",
        "users",
        type_="check",
    )
    op.drop_constraint(
        "ck_users_next_level_xp_non_negative",
        "users",
        type_="check",
    )
    op.drop_constraint("ck_users_xp_non_negative", "users", type_="check")
    op.drop_constraint("ck_users_level_progress_range", "users", type_="check")
    op.drop_constraint("ck_users_level_positive", "users", type_="check")
    op.drop_constraint(
        "ck_users_rank_positive_or_null",
        "users",
        type_="check",
    )
    op.drop_column("users", "season_label")
    op.drop_column("users", "streak_days")
    op.drop_column("users", "next_level_xp")
    op.drop_column("users", "xp")
    op.drop_column("users", "level_progress")
    op.drop_column("users", "level")
    op.drop_column("users", "rank")
    op.drop_column("users", "public_id")
    op.drop_column("users", "display_name")
