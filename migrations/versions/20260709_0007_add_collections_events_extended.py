"""Add collections, extended events, daily reward

Revision ID: 20260709_0007
Revises: 20260709_0006
Create Date: 2026-07-09 00:01:00.000000

Changes:
  1. collections + collection_items + user_collections
  2. events: add event_type column + description
  3. event_modifiers, event_items, event_goals, user_events
  4. item_secrets: add event_id FK
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260709_0007"
down_revision: str | Sequence[str] | None = "20260709_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────
    # 1. Collections
    # ──────────────────────────────────────────────────────────
    op.create_table(
        "collections",
        sa.Column("id", sa.String(96), nullable=False, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("reward_xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reward_item_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
        ),
        sa.ForeignKeyConstraint(
            ["reward_item_id"],
            ["items.id"],
            ondelete="SET NULL",
            name="fk_collections_reward_item_id_items",
        ),
        sa.CheckConstraint(
            "reward_xp >= 0",
            name="ck_collections_reward_xp_non_negative",
        ),
    )
    op.create_index("ix_collections_active", "collections", ["is_active"])

    op.create_table(
        "collection_items",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("collection_id", sa.String(96), nullable=False),
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.id"],
            ondelete="CASCADE",
            name="fk_collection_items_collection_id",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            ondelete="CASCADE",
            name="fk_collection_items_item_id",
        ),
        sa.UniqueConstraint("collection_id", "item_id", name="ux_collection_items"),
    )
    op.create_index("ix_collection_items_collection_id", "collection_items", ["collection_id"])
    op.create_index("ix_collection_items_item_id", "collection_items", ["item_id"])

    op.create_table(
        "user_collections",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("collection_id", sa.String(96), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_user_collections_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.id"],
            ondelete="CASCADE",
            name="fk_user_collections_collection_id",
        ),
        sa.UniqueConstraint("user_id", "collection_id", name="ux_user_collections"),
    )
    op.create_index("ix_user_collections_user_id", "user_collections", ["user_id"])

    # ──────────────────────────────────────────────────────────
    # 2. Extend events table
    # ──────────────────────────────────────────────────────────
    event_type_enum = postgresql.ENUM(
        "xp_boost",
        "thematic",
        "location",
        "community_goal",
        "personal_challenge",
        name="eventtype",
        create_type=True,
    )
    event_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "events",
        sa.Column(
            "event_type",
            event_type_enum,
            nullable=False,
            server_default="xp_boost",
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "events",
        sa.Column("max_participants", sa.Integer(), nullable=True),
    )

    # ──────────────────────────────────────────────────────────
    # 3. Event-related tables
    # ──────────────────────────────────────────────────────────
    op.create_table(
        "event_modifiers",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("event_id", sa.String(96), nullable=False),
        sa.Column("modifier_type", sa.String(64), nullable=False),
        sa.Column("value", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            ondelete="CASCADE",
            name="fk_event_modifiers_event_id",
        ),
    )
    op.create_index("ix_event_modifiers_event_id", "event_modifiers", ["event_id"])

    op.create_table(
        "event_items",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("event_id", sa.String(96), nullable=False),
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            ondelete="CASCADE",
            name="fk_event_items_event_id",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            ondelete="CASCADE",
            name="fk_event_items_item_id",
        ),
        sa.UniqueConstraint("event_id", "item_id", name="ux_event_items"),
    )

    op.create_table(
        "event_goals",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("event_id", sa.String(96), nullable=False, unique=True),
        sa.Column("target_value", sa.Integer(), nullable=False),
        sa.Column("current_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reward_xp", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            ondelete="CASCADE",
            name="fk_event_goals_event_id",
        ),
        sa.CheckConstraint(
            "target_value > 0",
            name="ck_event_goals_target_positive",
        ),
        sa.CheckConstraint(
            "current_value >= 0",
            name="ck_event_goals_current_non_negative",
        ),
        sa.CheckConstraint(
            "reward_xp >= 0",
            name="ck_event_goals_reward_xp_non_negative",
        ),
    )

    op.create_table(
        "user_events",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("event_id", sa.String(96), nullable=False),
        sa.Column(
            "joined_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "reward_claimed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_user_events_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            ondelete="CASCADE",
            name="fk_user_events_event_id",
        ),
        sa.UniqueConstraint("user_id", "event_id", name="ux_user_events"),
    )
    op.create_index("ix_user_events_user_id", "user_events", ["user_id"])
    op.create_index("ix_user_events_event_id", "user_events", ["event_id"])

    # ──────────────────────────────────────────────────────────
    # 4. item_secrets: add event_id FK
    # ──────────────────────────────────────────────────────────
    op.add_column(
        "item_secrets",
        sa.Column("event_id", sa.String(96), nullable=True),
    )
    op.create_foreign_key(
        "fk_item_secrets_event_id_events",
        "item_secrets",
        "events",
        ["event_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_item_secrets_event_id", "item_secrets", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_item_secrets_event_id", table_name="item_secrets")
    op.drop_constraint("fk_item_secrets_event_id_events", "item_secrets", type_="foreignkey")
    op.drop_column("item_secrets", "event_id")

    op.drop_table("user_events")
    op.drop_table("event_goals")
    op.drop_table("event_items")
    op.drop_table("event_modifiers")

    op.drop_column("events", "max_participants")
    op.drop_column("events", "description")
    op.drop_column("events", "event_type")
    postgresql.ENUM(name="eventtype").drop(op.get_bind(), checkfirst=True)

    op.drop_table("user_collections")
    op.drop_table("collection_items")
    op.drop_table("collections")
