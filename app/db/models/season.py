from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Index
from sqlmodel import Field, String

from app.db.models.base import BaseSQLModel


class Season(BaseSQLModel, table=True):
    __tablename__ = "seasons"
    __table_args__ = (
        Index("ix_seasons_is_active", "is_active"),
    )

    name: str = Field(sa_type=String(128), nullable=False)
    starts_at: datetime = Field(sa_type=DateTime(timezone=True), nullable=False)
    ends_at: datetime = Field(sa_type=DateTime(timezone=True), nullable=False)
    is_active: bool = Field(default=False, nullable=False)


class UserSeasonHistory(BaseSQLModel, table=True):
    __tablename__ = "user_season_history"
    __table_args__ = (
        Index("ux_user_season", "user_id", "season_id", unique=True),
        Index("ix_user_season_history_user_id", "user_id"),
        Index("ix_user_season_history_season_id", "season_id"),
    )

    user_id: int = Field(sa_type=BigInteger, nullable=False, foreign_key="users.id")
    season_id: int = Field(nullable=False, foreign_key="seasons.id")
    
    final_xp: int = Field(default=0, nullable=False)
    final_level: int = Field(default=1, nullable=False)
    final_rank: int | None = Field(default=None, nullable=True)
