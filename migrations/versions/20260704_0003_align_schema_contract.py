"""align schema contract

Revision ID: 20260704_0003
Revises: 20260629_0002
Create Date: 2026-07-04 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260704_0003"
down_revision: str | Sequence[str] | None = "20260629_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def recreate_foreign_key(
    *,
    table_name: str,
    old_name: str,
    new_name: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    ondelete: str | None = None,
) -> None:
    op.drop_constraint(old_name, table_name, type_="foreignkey")
    op.create_foreign_key(
        new_name,
        table_name,
        referent_table,
        local_cols,
        remote_cols,
        ondelete=ondelete,
    )


def upgrade() -> None:
    op.alter_column(
        "refresh_sessions",
        "token_hash",
        existing_type=sa.String(length=64),
        type_=sa.CHAR(length=64),
        postgresql_using="token_hash::char(64)",
    )
    op.alter_column(
        "item_secrets",
        "secret_hash",
        existing_type=sa.String(length=64),
        type_=sa.CHAR(length=64),
        postgresql_using="secret_hash::char(64)",
    )

    recreate_foreign_key(
        table_name="refresh_sessions",
        old_name="refresh_sessions_user_id_fkey",
        new_name="fk_refresh_sessions_user_id_users",
        referent_table="users",
        local_cols=["user_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    recreate_foreign_key(
        table_name="refresh_sessions",
        old_name="refresh_sessions_replaced_by_session_id_fkey",
        new_name="fk_refresh_sessions_replaced_by_session_id_refresh_sessions",
        referent_table="refresh_sessions",
        local_cols=["replaced_by_session_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )
    recreate_foreign_key(
        table_name="prototypes",
        old_name="prototypes_type_id_fkey",
        new_name="fk_prototypes_type_id_types",
        referent_table="types",
        local_cols=["type_id"],
        remote_cols=["id"],
    )
    recreate_foreign_key(
        table_name="items",
        old_name="items_category_id_fkey",
        new_name="fk_items_category_id_categories",
        referent_table="categories",
        local_cols=["category_id"],
        remote_cols=["id"],
    )
    recreate_foreign_key(
        table_name="items",
        old_name="items_prototype_id_fkey",
        new_name="fk_items_prototype_id_prototypes",
        referent_table="prototypes",
        local_cols=["prototype_id"],
        remote_cols=["id"],
    )
    recreate_foreign_key(
        table_name="items",
        old_name="items_type_id_fkey",
        new_name="fk_items_type_id_types",
        referent_table="types",
        local_cols=["type_id"],
        remote_cols=["id"],
    )
    recreate_foreign_key(
        table_name="item_images",
        old_name="item_images_item_id_fkey",
        new_name="fk_item_images_item_id_items",
        referent_table="items",
        local_cols=["item_id"],
        remote_cols=["id"],
    )
    recreate_foreign_key(
        table_name="item_secrets",
        old_name="item_secrets_item_id_fkey",
        new_name="fk_item_secrets_item_id_items",
        referent_table="items",
        local_cols=["item_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    recreate_foreign_key(
        table_name="validations",
        old_name="validations_user_id_fkey",
        new_name="fk_validations_user_id_users",
        referent_table="users",
        local_cols=["user_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    recreate_foreign_key(
        table_name="validations",
        old_name="validations_item_id_fkey",
        new_name="fk_validations_item_id_items",
        referent_table="items",
        local_cols=["item_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    recreate_foreign_key(
        table_name="validations",
        old_name="validations_item_secret_id_fkey",
        new_name="fk_validations_item_secret_id_item_secrets",
        referent_table="item_secrets",
        local_cols=["item_secret_id"],
        remote_cols=["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    recreate_foreign_key(
        table_name="refresh_sessions",
        old_name="fk_refresh_sessions_user_id_users",
        new_name="refresh_sessions_user_id_fkey",
        referent_table="users",
        local_cols=["user_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    recreate_foreign_key(
        table_name="refresh_sessions",
        old_name="fk_refresh_sessions_replaced_by_session_id_refresh_sessions",
        new_name="refresh_sessions_replaced_by_session_id_fkey",
        referent_table="refresh_sessions",
        local_cols=["replaced_by_session_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )
    recreate_foreign_key(
        table_name="prototypes",
        old_name="fk_prototypes_type_id_types",
        new_name="prototypes_type_id_fkey",
        referent_table="types",
        local_cols=["type_id"],
        remote_cols=["id"],
    )
    recreate_foreign_key(
        table_name="items",
        old_name="fk_items_category_id_categories",
        new_name="items_category_id_fkey",
        referent_table="categories",
        local_cols=["category_id"],
        remote_cols=["id"],
    )
    recreate_foreign_key(
        table_name="items",
        old_name="fk_items_prototype_id_prototypes",
        new_name="items_prototype_id_fkey",
        referent_table="prototypes",
        local_cols=["prototype_id"],
        remote_cols=["id"],
    )
    recreate_foreign_key(
        table_name="items",
        old_name="fk_items_type_id_types",
        new_name="items_type_id_fkey",
        referent_table="types",
        local_cols=["type_id"],
        remote_cols=["id"],
    )
    recreate_foreign_key(
        table_name="item_images",
        old_name="fk_item_images_item_id_items",
        new_name="item_images_item_id_fkey",
        referent_table="items",
        local_cols=["item_id"],
        remote_cols=["id"],
    )
    recreate_foreign_key(
        table_name="item_secrets",
        old_name="fk_item_secrets_item_id_items",
        new_name="item_secrets_item_id_fkey",
        referent_table="items",
        local_cols=["item_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    recreate_foreign_key(
        table_name="validations",
        old_name="fk_validations_user_id_users",
        new_name="validations_user_id_fkey",
        referent_table="users",
        local_cols=["user_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    recreate_foreign_key(
        table_name="validations",
        old_name="fk_validations_item_id_items",
        new_name="validations_item_id_fkey",
        referent_table="items",
        local_cols=["item_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    recreate_foreign_key(
        table_name="validations",
        old_name="fk_validations_item_secret_id_item_secrets",
        new_name="validations_item_secret_id_fkey",
        referent_table="item_secrets",
        local_cols=["item_secret_id"],
        remote_cols=["id"],
        ondelete="RESTRICT",
    )

    op.alter_column(
        "item_secrets",
        "secret_hash",
        existing_type=sa.CHAR(length=64),
        type_=sa.String(length=64),
        postgresql_using="trim(trailing from secret_hash)",
    )
    op.alter_column(
        "refresh_sessions",
        "token_hash",
        existing_type=sa.CHAR(length=64),
        type_=sa.String(length=64),
        postgresql_using="trim(trailing from token_hash)",
    )
