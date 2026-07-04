from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Index, Numeric, String, text
from sqlmodel import Field

from app.db.models.base import SlugSQLModel
from app.db.models.enums import Rarity, rarity_sa_enum


class Event(SlugSQLModel, table=True):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(
            "xp_multiplier > 0",
            name="ck_events_xp_multiplier_positive",
        ),
        CheckConstraint("ends_at > starts_at", name="ck_events_period_valid"),
        Index("ix_events_active", "is_active"),
        Index("ix_events_active_ends_at", "is_active", "ends_at"),
        Index("ix_events_rarity", "rarity"),
    )

    title: str = Field(sa_type=String(180), nullable=False)
    rarity: Rarity = Field(sa_type=rarity_sa_enum(), nullable=False)
    xp_multiplier: Decimal = Field(
        default=Decimal("1.00"),
        sa_type=Numeric(5, 2),
        nullable=False,
        sa_column_kwargs={"server_default": "1"},
    )
    starts_at: datetime = Field(sa_type=DateTime(timezone=True), nullable=False)
    ends_at: datetime = Field(sa_type=DateTime(timezone=True), nullable=False)
    is_active: bool = Field(
        default=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("true")},
    )
