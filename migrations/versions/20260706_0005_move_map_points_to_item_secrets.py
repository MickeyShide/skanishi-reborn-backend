"""move map points to item secrets

Revision ID: 20260706_0005
Revises: 20260704_0004
Create Date: 2026-07-06 00:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260706_0005"
down_revision: str | Sequence[str] | None = "20260704_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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


def slug_id_column() -> sa.Column:
    return sa.Column(
        "id",
        sa.String(length=96),
        primary_key=True,
        nullable=False,
    )


def upgrade() -> None:
    rarity = rarity_enum()

    op.add_column(
        "item_secrets",
        sa.Column(
            "category",
            sa.String(length=64),
            server_default="Секрет",
            nullable=False,
        ),
    )
    op.add_column(
        "item_secrets",
        sa.Column("rarity", rarity, server_default="rare", nullable=False),
    )
    op.add_column(
        "item_secrets",
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
    )
    op.add_column(
        "item_secrets",
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
    )
    op.add_column(
        "item_secrets",
        sa.Column("reward_xp", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "item_secrets",
        sa.Column("description", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "item_secrets",
        sa.Column("quest_id", sa.String(length=96), nullable=True),
    )
    op.add_column(
        "item_secrets",
        sa.Column(
            "is_big",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "item_secrets",
        sa.Column(
            "has_hint",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "item_secrets",
        sa.Column(
            "hidden",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.execute(
        """
        UPDATE item_secrets
        SET
            latitude = CASE 
                WHEN trim(split_part(coords, ',', 1))::numeric BETWEEN -90 AND 90 
                THEN trim(split_part(coords, ',', 1))::numeric 
                WHEN trim(split_part(coords, ',', 2))::numeric BETWEEN -90 AND 90
                THEN trim(split_part(coords, ',', 2))::numeric
                ELSE NULL
            END,
            longitude = CASE 
                WHEN trim(split_part(coords, ',', 1))::numeric BETWEEN -90 AND 90 
                THEN trim(split_part(coords, ',', 2))::numeric 
                WHEN trim(split_part(coords, ',', 2))::numeric BETWEEN -90 AND 90
                THEN trim(split_part(coords, ',', 1))::numeric
                ELSE NULL
            END
        WHERE coords ~ '^\\s*-?[0-9]+(\\.[0-9]+)?\\s*,\\s*-?[0-9]+(\\.[0-9]+)?\\s*$'
        """
    )

    op.create_foreign_key(
        "fk_item_secrets_quest_id_quests",
        "item_secrets",
        "quests",
        ["quest_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_item_secrets_latitude_range",
        "item_secrets",
        "latitude IS NULL OR latitude BETWEEN -90 AND 90",
    )
    op.create_check_constraint(
        "ck_item_secrets_longitude_range",
        "item_secrets",
        "longitude IS NULL OR longitude BETWEEN -180 AND 180",
    )
    op.create_check_constraint(
        "ck_item_secrets_reward_xp_non_negative",
        "item_secrets",
        "reward_xp >= 0",
    )
    op.create_index("ix_item_secrets_hidden", "item_secrets", ["hidden"])
    op.create_index("ix_item_secrets_rarity", "item_secrets", ["rarity"])
    op.create_index(
        "ix_item_secrets_lat_lon",
        "item_secrets",
        ["latitude", "longitude"],
    )
    op.create_index("ix_item_secrets_quest_id", "item_secrets", ["quest_id"])

    op.drop_index("ix_map_points_quest_id", table_name="map_points")
    op.drop_index("ix_map_points_lat_lon", table_name="map_points")
    op.drop_index("ix_map_points_rarity", table_name="map_points")
    op.drop_index("ix_map_points_active", table_name="map_points")
    op.drop_table("map_points")


def downgrade() -> None:
    rarity = rarity_enum()

    op.create_table(
        "map_points",
        slug_id_column(),
        *timestamps(),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("rarity", rarity, nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("reward_xp", sa.Integer(), server_default="0", nullable=False),
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

    op.drop_index("ix_item_secrets_quest_id", table_name="item_secrets")
    op.drop_index("ix_item_secrets_lat_lon", table_name="item_secrets")
    op.drop_index("ix_item_secrets_rarity", table_name="item_secrets")
    op.drop_index("ix_item_secrets_hidden", table_name="item_secrets")
    op.drop_constraint(
        "ck_item_secrets_reward_xp_non_negative",
        "item_secrets",
        type_="check",
    )
    op.drop_constraint(
        "ck_item_secrets_longitude_range",
        "item_secrets",
        type_="check",
    )
    op.drop_constraint(
        "ck_item_secrets_latitude_range",
        "item_secrets",
        type_="check",
    )
    op.drop_constraint(
        "fk_item_secrets_quest_id_quests",
        "item_secrets",
        type_="foreignkey",
    )
    op.drop_column("item_secrets", "hidden")
    op.drop_column("item_secrets", "has_hint")
    op.drop_column("item_secrets", "is_big")
    op.drop_column("item_secrets", "quest_id")
    op.drop_column("item_secrets", "description")
    op.drop_column("item_secrets", "reward_xp")
    op.drop_column("item_secrets", "longitude")
    op.drop_column("item_secrets", "latitude")
    op.drop_column("item_secrets", "rarity")
    op.drop_column("item_secrets", "category")
