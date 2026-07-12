from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    text,
)
from sqlmodel import Field, Index, Text

from app.db.models.base import BaseSQLModel
from app.db.models.enums import Rarity, rarity_sa_enum


class ItemSecret(BaseSQLModel, table=True):
    __tablename__ = "item_secrets"

    item_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "items.id",
                ondelete="CASCADE",
                name="fk_item_secrets_item_id_items",
            ),
            nullable=False,
        ),
    )

    secret_hash: str = Field(
        sa_type=CHAR(64),
        nullable=False,
    )

    title: str = Field(sa_type=String(128), nullable=False)
    coords: str | None = Field(default=None, sa_type=String(128), nullable=True)
    category: str = Field(
        default="Секрет",
        sa_type=String(64),
        nullable=False,
        sa_column_kwargs={"server_default": "Секрет"},
    )
    rarity: Rarity = Field(
        default=Rarity.RARE,
        sa_type=rarity_sa_enum(),
        nullable=False,
        sa_column_kwargs={"server_default": Rarity.RARE.value},
    )
    latitude: Decimal | None = Field(default=None, sa_type=Numeric(9, 6), nullable=True)
    longitude: Decimal | None = Field(
        default=None,
        sa_type=Numeric(9, 6),
        nullable=True,
    )
    reward_xp: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )
    description: str = Field(
        default="",
        sa_type=Text,
        nullable=False,
        sa_column_kwargs={"server_default": ""},
    )
    quest_id: str | None = Field(
        default=None,
        sa_column=Column(
            String(96),
            ForeignKey(
                "quests.id",
                ondelete="SET NULL",
                name="fk_item_secrets_quest_id_quests",
            ),
            nullable=True,
        ),
    )
    is_big: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": text("false")},
    )
    has_hint: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": text("false")},
    )
    hidden: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": text("false")},
    )
    is_active: bool = Field(
        default=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("true")},
    )

    validation_count: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )
    
    cooldown_until: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True), nullable=True
    )

    expires_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ux_item_secrets_secret_hash", "secret_hash", unique=True),
        Index("ix_item_secrets_item_id", "item_id"),
        Index("ix_item_secrets_active", "is_active"),
        Index("ix_item_secrets_hidden", "hidden"),
        Index("ix_item_secrets_rarity", "rarity"),
        Index("ix_item_secrets_lat_lon", "latitude", "longitude"),
        Index("ix_item_secrets_quest_id", "quest_id"),
        CheckConstraint(
            "latitude IS NULL OR latitude BETWEEN -90 AND 90",
            name="ck_item_secrets_latitude_range",
        ),
        CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180",
            name="ck_item_secrets_longitude_range",
        ),
        CheckConstraint(
            "reward_xp >= 0",
            name="ck_item_secrets_reward_xp_non_negative",
        ),
    )
