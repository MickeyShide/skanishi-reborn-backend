from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Index
from sqlmodel import Field, String, Text

from app.db.models.base import BaseSQLModel, SlugSQLModel
from app.db.models.enums import Rarity, rarity_sa_enum


class Achievement(SlugSQLModel, table=True):
    __tablename__ = "achievements"
    __table_args__ = (
        CheckConstraint(
            "reward_xp >= 0",
            name="ck_achievements_reward_xp_non_negative",
        ),
        Index("ix_achievements_rarity", "rarity"),
    )

    icon: str = Field(sa_type=String(32), nullable=False)
    name: str = Field(sa_type=String(128), nullable=False)
    rarity: Rarity = Field(sa_type=rarity_sa_enum(), nullable=False)
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


class UserAchievement(BaseSQLModel, table=True):
    __tablename__ = "user_achievements"
    __table_args__ = (
        CheckConstraint(
            "progress_percent BETWEEN 0 AND 100",
            name="ck_user_achievements_progress_percent_range",
        ),
        Index(
            "ux_user_achievements_user_achievement",
            "user_id",
            "achievement_id",
            unique=True,
        ),
        Index("ix_user_achievements_user_id", "user_id"),
        Index("ix_user_achievements_achievement_id", "achievement_id"),
        Index("ix_user_achievements_unlocked", "unlocked"),
    )

    user_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "users.id",
                ondelete="CASCADE",
                name="fk_user_achievements_user_id_users",
            ),
            nullable=False,
        ),
    )
    achievement_id: str = Field(
        sa_column=Column(
            String(96),
            ForeignKey(
                "achievements.id",
                ondelete="CASCADE",
                name="fk_user_achievements_achievement_id_achievements",
            ),
            nullable=False,
        ),
    )
    unlocked: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": "false"},
    )
    progress_percent: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )
    unlocked_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )
