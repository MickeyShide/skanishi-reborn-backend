from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
)
from sqlmodel import Field, String

from app.db.models.base import BaseSQLModel
from app.db.models.enums import UIColorToken, ui_color_token_sa_enum


class XpEvent(BaseSQLModel, table=True):
    __tablename__ = "xp_events"
    __table_args__ = (
        CheckConstraint(
            "multiplier IS NULL OR multiplier > 0",
            name="ck_xp_events_multiplier_positive_or_null",
        ),
    )

    user_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "users.id",
                ondelete="CASCADE",
                name="fk_xp_events_user_id_users",
            ),
            nullable=False,
        ),
    )
    source: str = Field(sa_type=String(180), nullable=False)
    tag: str | None = Field(default=None, sa_type=String(32), nullable=True)
    xp: int = Field(nullable=False)
    multiplier: Decimal | None = Field(
        default=None,
        sa_type=Numeric(5, 2),
        nullable=True,
    )
    color: UIColorToken | None = Field(
        default=None,
        sa_type=ui_color_token_sa_enum(),
        nullable=True,
    )
    occurred_at: datetime = Field(sa_type=DateTime(timezone=True), nullable=False)


Index(
    "ix_xp_events_user_occurred",
    XpEvent.__table__.c.user_id,
    XpEvent.__table__.c.occurred_at.desc(),
)
Index(
    "ux_xp_events_user_source",
    "user_id",
    "source",
    unique=True,
)
