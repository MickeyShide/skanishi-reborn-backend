from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Index, Numeric, text
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, String

from app.db.models.base import BaseSQLModel


class EventType(StrEnum):
    XP_BOOST = "xp_boost"
    THEMATIC = "thematic"
    LOCATION = "location"
    COMMUNITY_GOAL = "community_goal"
    PERSONAL_CHALLENGE = "personal_challenge"


def _event_type_sa_enum() -> SAEnum:
    return SAEnum(
        EventType,
        values_callable=lambda e: [m.value for m in e],
        name="eventtype",
    )


class EventModifier(BaseSQLModel, table=True):
    """Additional modifier attached to an Event.

    For example: an event might have an xp_multiplier modifier (3.0) AND
    a special item-drop-rate modifier (2.0).  Modifiers are additive to the
    base event xp_multiplier.
    """

    __tablename__ = "event_modifiers"
    __table_args__ = (
        Index("ix_event_modifiers_event_id", "event_id"),
    )

    event_id: str = Field(
        sa_column=Column(
            String(96),
            ForeignKey(
                "events.id",
                ondelete="CASCADE",
                name="fk_event_modifiers_event_id",
            ),
            nullable=False,
        ),
    )
    modifier_type: str = Field(sa_type=String(64), nullable=False)
    value: Decimal = Field(sa_type=Numeric(10, 2), nullable=False)


class EventItem(BaseSQLModel, table=True):
    """Item available exclusively during a specific event."""

    __tablename__ = "event_items"
    __table_args__ = (
        Index("ux_event_items", "event_id", "item_id", unique=True),
    )

    event_id: str = Field(
        sa_column=Column(
            String(96),
            ForeignKey(
                "events.id",
                ondelete="CASCADE",
                name="fk_event_items_event_id",
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
                name="fk_event_items_item_id",
            ),
            nullable=False,
        ),
    )


class EventGoal(BaseSQLModel, table=True):
    """Community goal attached to an event.

    All participants collectively contribute to `current_value`.
    When it reaches `target_value` the event is considered a community success
    and `reward_xp` is granted to all participants.
    """

    __tablename__ = "event_goals"
    __table_args__ = (
        CheckConstraint("target_value > 0", name="ck_event_goals_target_positive"),
        CheckConstraint(
            "current_value >= 0",
            name="ck_event_goals_current_non_negative",
        ),
        CheckConstraint(
            "reward_xp >= 0",
            name="ck_event_goals_reward_xp_non_negative",
        ),
    )

    event_id: str = Field(
        sa_column=Column(
            String(96),
            ForeignKey(
                "events.id",
                ondelete="CASCADE",
                name="fk_event_goals_event_id",
            ),
            nullable=False,
            unique=True,
        ),
    )
    target_value: int = Field(nullable=False)
    current_value: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )
    reward_xp: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )


class UserEvent(BaseSQLModel, table=True):
    """Records a user's participation in an event."""

    __tablename__ = "user_events"
    __table_args__ = (
        Index("ux_user_events", "user_id", "event_id", unique=True),
        Index("ix_user_events_user_id", "user_id"),
        Index("ix_user_events_event_id", "event_id"),
    )

    user_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "users.id",
                ondelete="CASCADE",
                name="fk_user_events_user_id",
            ),
            nullable=False,
        ),
    )
    event_id: str = Field(
        sa_column=Column(
            String(96),
            ForeignKey(
                "events.id",
                ondelete="CASCADE",
                name="fk_user_events_event_id",
            ),
            nullable=False,
        ),
    )
    joined_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": "now()"},
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
