from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Index, text
from sqlmodel import Field, String, Text

from app.db.models.base import BaseSQLModel, SlugSQLModel


class Collection(SlugSQLModel, table=True):
    """A named group of items that can be completed as a set.

    When a user acquires every item in the collection the completion
    worker grants the collection reward.
    """

    __tablename__ = "collections"
    __table_args__ = (
        CheckConstraint(
            "reward_xp >= 0",
            name="ck_collections_reward_xp_non_negative",
        ),
        Index("ix_collections_active", "is_active"),
    )

    name: str = Field(sa_type=String(128), nullable=False)
    description: str = Field(
        default="",
        sa_type=Text,
        nullable=False,
        sa_column_kwargs={"server_default": ""},
    )
    reward_xp: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )
    reward_item_id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "items.id",
                ondelete="SET NULL",
                name="fk_collections_reward_item_id_items",
            ),
            nullable=True,
        ),
    )
    is_active: bool = Field(
        default=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("true")},
    )


class CollectionItem(BaseSQLModel, table=True):
    """Association between a Collection and an Item."""

    __tablename__ = "collection_items"
    __table_args__ = (
        Index("ux_collection_items", "collection_id", "item_id", unique=True),
        Index("ix_collection_items_collection_id", "collection_id"),
        Index("ix_collection_items_item_id", "item_id"),
    )

    collection_id: str = Field(
        sa_column=Column(
            String(96),
            ForeignKey(
                "collections.id",
                ondelete="CASCADE",
                name="fk_collection_items_collection_id",
            ),
            nullable=False,
        ),
    )
    item_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "items.id",
                ondelete="CASCADE",
                name="fk_collection_items_item_id",
            ),
            nullable=False,
        ),
    )


class UserCollection(BaseSQLModel, table=True):
    """Tracks a user's progress toward completing a collection."""

    __tablename__ = "user_collections"
    __table_args__ = (
        Index("ux_user_collections", "user_id", "collection_id", unique=True),
        Index("ix_user_collections_user_id", "user_id"),
    )

    user_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "users.id",
                ondelete="CASCADE",
                name="fk_user_collections_user_id",
            ),
            nullable=False,
        ),
    )
    collection_id: str = Field(
        sa_column=Column(
            String(96),
            ForeignKey(
                "collections.id",
                ondelete="CASCADE",
                name="fk_user_collections_collection_id",
            ),
            nullable=False,
        ),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )
    reward_claimed: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": text("false")},
    )
