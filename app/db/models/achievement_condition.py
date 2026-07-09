from __future__ import annotations

from enum import StrEnum

from sqlalchemy import BigInteger, CheckConstraint, Column, ForeignKey, Index, Integer
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, String

from app.db.models.base import BaseSQLModel


class AchievementConditionType(StrEnum):
    SCAN_COUNT = "scan_count"
    XP_TOTAL = "xp_total"
    LEVEL_REACHED = "level_reached"
    COLLECTION_COMPLETE = "collection_complete"
    STREAK_DAYS = "streak_days"
    QUEST_COUNT = "quest_count"


def _condition_type_sa_enum() -> SAEnum:
    return SAEnum(
        AchievementConditionType,
        values_callable=lambda e: [m.value for m in e],
        name="achievementconditiontype",
    )


class AchievementCondition(BaseSQLModel, table=True):
    """Typed trigger condition for automatic achievement unlocking.

    The achievement-checker worker reads all conditions for each achievement
    and evaluates whether the user has met every condition.  All conditions
    on a single achievement are AND-combined.
    """

    __tablename__ = "achievement_conditions"
    __table_args__ = (
        CheckConstraint(
            "threshold > 0",
            name="ck_achievement_conditions_threshold_positive",
        ),
        Index(
            "ix_achievement_conditions_achievement_id",
            "achievement_id",
        ),
    )

    achievement_id: str = Field(
        sa_column=Column(
            String(96),
            ForeignKey(
                "achievements.id",
                ondelete="CASCADE",
                name="fk_achievement_conditions_achievement_id",
            ),
            nullable=False,
        ),
    )
    condition_type: AchievementConditionType = Field(
        sa_type=_condition_type_sa_enum(),
        nullable=False,
    )
    threshold: int = Field(nullable=False)
