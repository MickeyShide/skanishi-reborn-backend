from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Index, text
from sqlmodel import Field, Integer, String

from app.db.models.base import BaseSQLModel


class UserQuest(BaseSQLModel, table=True):
    """Per-user quest progress.

    Each row tracks a single user's progress toward a specific quest.
    The `progress` field stores an absolute count (number of scans, items, etc.)
    that the quest-checker worker increments.  When progress reaches the
    quest's target the worker sets `completed_at`.
    """

    __tablename__ = "user_quests"
    __table_args__ = (
        CheckConstraint(
            "progress >= 0",
            name="ck_user_quests_progress_non_negative",
        ),
        Index("ux_user_quests_user_quest", "user_id", "quest_id", unique=True),
        Index("ix_user_quests_user_id", "user_id"),
        Index("ix_user_quests_quest_id", "quest_id"),
        Index("ix_user_quests_completed", "user_id", "completed_at"),
    )

    user_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "users.id",
                ondelete="CASCADE",
                name="fk_user_quests_user_id_users",
            ),
            nullable=False,
        ),
    )
    quest_id: str = Field(
        sa_column=Column(
            String(96),
            ForeignKey(
                "quests.id",
                ondelete="CASCADE",
                name="fk_user_quests_quest_id_quests",
            ),
            nullable=False,
        ),
    )
    progress: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
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
