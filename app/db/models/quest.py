from sqlalchemy import CheckConstraint, Index, text
from sqlmodel import Field, String

from app.db.models.base import SlugSQLModel
from app.db.models.enums import Rarity, rarity_sa_enum


class Quest(SlugSQLModel, table=True):
    __tablename__ = "quests"
    __table_args__ = (
        CheckConstraint(
            "progress_percent BETWEEN 0 AND 100",
            name="ck_quests_progress_percent_range",
        ),
        CheckConstraint(
            "reward_xp >= 0",
            name="ck_quests_reward_xp_non_negative",
        ),
        Index("ix_quests_active", "is_active"),
        Index("ix_quests_rarity", "rarity"),
        Index("ix_quests_season_id", "season_id"),
    )

    name: str = Field(sa_type=String(160), nullable=False)
    step_label: str = Field(sa_type=String(80), nullable=False)
    progress_percent: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )
    rarity: Rarity = Field(sa_type=rarity_sa_enum(), nullable=False)
    reward_xp: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )
    season_id: str | None = Field(default=None, sa_type=String(96), nullable=True)
    is_active: bool = Field(
        default=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("true")},
    )
