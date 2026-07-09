from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, Index, text
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, String, Text

from app.db.models.base import BaseSQLModel


class UserRole(StrEnum):
    USER = "USER"
    MOD = "MOD"
    ADMIN = "ADMIN"


class User(BaseSQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "rank IS NULL OR rank > 0",
            name="ck_users_rank_positive_or_null",
        ),
        CheckConstraint("level > 0", name="ck_users_level_positive"),
        CheckConstraint(
            "level_progress BETWEEN 0 AND 100",
            name="ck_users_level_progress_range",
        ),
        CheckConstraint("xp >= 0", name="ck_users_xp_non_negative"),
        CheckConstraint(
            "next_level_xp >= 0",
            name="ck_users_next_level_xp_non_negative",
        ),
        CheckConstraint(
            "streak_days >= 0",
            name="ck_users_streak_days_non_negative",
        ),
        Index("ux_users_tg_id", "tg_id", unique=True),
        Index(
            "ux_users_username_not_null",
            "username",
            unique=True,
            postgresql_where=text("username IS NOT NULL"),
        ),
        Index(
            "ux_users_public_id_not_null",
            "public_id",
            unique=True,
            postgresql_where=text("public_id IS NOT NULL"),
        ),
        Index("ix_users_role", "role"),
        Index("ix_users_rank", "rank"),
    )

    tg_id: int = Field(sa_type=BigInteger, nullable=False)
    is_private: bool = Field(
        default=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("true")},
    )

    first_name: str = Field(sa_type=String(128), nullable=False)
    last_name: str | None = Field(default=None, sa_type=String(128), nullable=True)
    is_premium: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": text("false")},
    )
    photo_url: str | None = Field(default=None, sa_type=Text, nullable=True)
    username: str | None = Field(default=None, sa_type=String(64), nullable=True)
    role: UserRole = Field(
        sa_type=SAEnum(UserRole, name="userrole"),
        default=UserRole.USER,
        nullable=False,
        sa_column_kwargs={"server_default": UserRole.USER.value},
    )
    display_name: str | None = Field(default=None, sa_type=String(160), nullable=True)
    public_id: str | None = Field(default=None, sa_type=String(64), nullable=True)
    rank: int | None = Field(default=None, nullable=True)
    level: int = Field(
        default=1,
        nullable=False,
        sa_column_kwargs={"server_default": "1"},
    )
    level_progress: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )
    xp: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )
    next_level_xp: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )
    streak_days: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )
    season_label: str | None = Field(default=None, sa_type=String(160), nullable=True)

    # ── Login / streak / daily tracking ──────────────────────────────────────
    last_login_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )
    last_daily_claimed_at: date | None = Field(
        default=None,
        sa_type=Date(),
        nullable=True,
    )
    streak_last_date: date | None = Field(
        default=None,
        sa_type=Date(),
        nullable=True,
    )
