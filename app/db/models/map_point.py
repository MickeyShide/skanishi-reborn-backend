from decimal import Decimal

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Numeric, String, text
from sqlmodel import Field, Text

from app.db.models.base import SlugSQLModel
from app.db.models.enums import Rarity, rarity_sa_enum


class MapPoint(SlugSQLModel, table=True):
    __tablename__ = "map_points"
    __table_args__ = (
        CheckConstraint(
            "latitude BETWEEN -90 AND 90",
            name="ck_map_points_latitude_range",
        ),
        CheckConstraint(
            "longitude BETWEEN -180 AND 180",
            name="ck_map_points_longitude_range",
        ),
        CheckConstraint(
            "reward_xp >= 0",
            name="ck_map_points_reward_xp_non_negative",
        ),
        Index("ix_map_points_active", "is_active"),
        Index("ix_map_points_rarity", "rarity"),
        Index("ix_map_points_lat_lon", "latitude", "longitude"),
        Index("ix_map_points_quest_id", "quest_id"),
    )

    name: str = Field(sa_type=String(160), nullable=False)
    category: str = Field(sa_type=String(64), nullable=False)
    rarity: Rarity = Field(sa_type=rarity_sa_enum(), nullable=False)
    latitude: Decimal = Field(sa_type=Numeric(9, 6), nullable=False)
    longitude: Decimal = Field(sa_type=Numeric(9, 6), nullable=False)
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
                name="fk_map_points_quest_id_quests",
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
    is_active: bool = Field(
        default=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("true")},
    )
