"""database models

Revision ID: 20260629_0002
Revises: 20260629_0001
Create Date: 2026-06-29 00:02:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260629_0002"
down_revision: str | Sequence[str] | None = "20260629_0001"
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


def upgrade() -> None:
    user_role = sa.Enum("USER", "MOD", "ADMIN", name="userrole")

    op.create_table(
        "users",
        id_column(),
        *timestamps(),
        sa.Column("tg_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "is_private",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("first_name", sa.String(length=128), nullable=False),
        sa.Column("last_name", sa.String(length=128), nullable=True),
        sa.Column(
            "is_premium",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("role", user_role, server_default="USER", nullable=False),
    )
    op.create_index("ux_users_tg_id", "users", ["tg_id"], unique=True)
    op.create_index(
        "ux_users_username_not_null",
        "users",
        ["username"],
        unique=True,
        postgresql_where=sa.text("username IS NOT NULL"),
    )
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "refresh_sessions",
        id_column(),
        *timestamps(),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("jti", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_session_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["replaced_by_session_id"],
            ["refresh_sessions.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"])
    op.create_index("ux_refresh_sessions_jti", "refresh_sessions", ["jti"], unique=True)
    op.create_index(
        "ux_refresh_sessions_token_hash",
        "refresh_sessions",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_refresh_sessions_expires_at",
        "refresh_sessions",
        ["expires_at"],
    )
    op.create_index(
        "ix_refresh_sessions_active",
        "refresh_sessions",
        ["id"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )

    op.create_table(
        "categories",
        id_column(),
        *timestamps(),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.CheckConstraint(
            "color ~ '^#[0-9A-Fa-f]{6}$' "
            "OR color IN ("
            "'primary', 'secondary', 'success', 'warning', "
            "'danger', 'info', 'neutral'"
            ")",
            name="ck_categories_color",
        ),
    )
    op.create_index("ux_categories_title", "categories", ["title"], unique=True)

    op.create_table(
        "types",
        id_column(),
        *timestamps(),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("photo_url", sa.Text(), nullable=True),
    )
    op.create_index("ux_types_title", "types", ["title"], unique=True)

    op.create_table(
        "prototypes",
        id_column(),
        *timestamps(),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("type_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["type_id"], ["types.id"]),
    )
    op.create_index("ix_prototypes_type_id", "prototypes", ["type_id"])

    op.create_table(
        "items",
        id_column(),
        *timestamps(),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("prototype_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("type_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "validation_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.CheckConstraint("number > 0", name="ck_items_number_positive"),
        sa.CheckConstraint(
            "validation_count >= 0",
            name="ck_items_validation_count_non_negative",
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["prototype_id"], ["prototypes.id"]),
        sa.ForeignKeyConstraint(["type_id"], ["types.id"]),
    )
    op.create_index("ux_items_number", "items", ["number"], unique=True)
    op.create_index("ix_items_category_id", "items", ["category_id"])
    op.create_index("ix_items_category_type", "items", ["category_id", "type_id"])
    op.create_index("ix_items_is_active", "items", ["is_active"])
    op.create_index("ix_items_prototype_id", "items", ["prototype_id"])
    op.create_index("ix_items_type_id", "items", ["type_id"])

    op.create_table(
        "item_images",
        id_column(),
        *timestamps(),
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column(
            "is_main",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
    )
    op.create_index("ix_item_images_item_id", "item_images", ["item_id"])
    op.create_index(
        "ux_item_images_one_main_per_item",
        "item_images",
        ["item_id"],
        unique=True,
        postgresql_where=sa.text("is_main = true"),
    )

    op.create_table(
        "item_secrets",
        id_column(),
        *timestamps(),
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("secret_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("coords", sa.String(length=128), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ux_item_secrets_secret_hash",
        "item_secrets",
        ["secret_hash"],
        unique=True,
    )
    op.create_index("ix_item_secrets_item_id", "item_secrets", ["item_id"])
    op.create_index("ix_item_secrets_active", "item_secrets", ["is_active"])

    op.create_table(
        "validations",
        id_column(),
        *timestamps(),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("item_secret_id", sa.BigInteger(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.CheckConstraint("rank > 0", name="ck_validations_rank_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["item_secret_id"],
            ["item_secrets.id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ux_validations_user_item",
        "validations",
        ["user_id", "item_id"],
        unique=True,
    )
    op.create_index(
        "ux_validations_item_rank",
        "validations",
        ["item_id", "rank"],
        unique=True,
    )
    op.create_index("ix_validations_user_id", "validations", ["user_id"])
    op.create_index("ix_validations_item_id", "validations", ["item_id"])
    op.create_index("ix_validations_item_secret_id", "validations", ["item_secret_id"])
    op.create_index(
        "ix_validations_item_created_at",
        "validations",
        ["item_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_validations_item_created_at", table_name="validations")
    op.drop_index("ix_validations_item_secret_id", table_name="validations")
    op.drop_index("ix_validations_item_id", table_name="validations")
    op.drop_index("ix_validations_user_id", table_name="validations")
    op.drop_index("ux_validations_item_rank", table_name="validations")
    op.drop_index("ux_validations_user_item", table_name="validations")
    op.drop_table("validations")

    op.drop_index("ix_item_secrets_active", table_name="item_secrets")
    op.drop_index("ix_item_secrets_item_id", table_name="item_secrets")
    op.drop_index("ux_item_secrets_secret_hash", table_name="item_secrets")
    op.drop_table("item_secrets")

    op.drop_index("ux_item_images_one_main_per_item", table_name="item_images")
    op.drop_index("ix_item_images_item_id", table_name="item_images")
    op.drop_table("item_images")

    op.drop_index("ix_items_type_id", table_name="items")
    op.drop_index("ix_items_prototype_id", table_name="items")
    op.drop_index("ix_items_is_active", table_name="items")
    op.drop_index("ix_items_category_type", table_name="items")
    op.drop_index("ix_items_category_id", table_name="items")
    op.drop_index("ux_items_number", table_name="items")
    op.drop_table("items")

    op.drop_index("ix_prototypes_type_id", table_name="prototypes")
    op.drop_table("prototypes")

    op.drop_index("ux_types_title", table_name="types")
    op.drop_table("types")

    op.drop_index("ux_categories_title", table_name="categories")
    op.drop_table("categories")

    op.drop_index("ix_refresh_sessions_active", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_expires_at", table_name="refresh_sessions")
    op.drop_index("ux_refresh_sessions_token_hash", table_name="refresh_sessions")
    op.drop_index("ux_refresh_sessions_jti", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_user_id", table_name="refresh_sessions")
    op.drop_table("refresh_sessions")

    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ux_users_username_not_null", table_name="users")
    op.drop_index("ux_users_tg_id", table_name="users")
    op.drop_table("users")
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
