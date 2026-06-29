from enum import StrEnum

from sqlalchemy import BigInteger, Index, text
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
        Index("ux_users_tg_id", "tg_id", unique=True),
        Index(
            "ux_users_username_not_null",
            "username",
            unique=True,
            postgresql_where=text("username IS NOT NULL"),
        ),
        Index("ix_users_role", "role"),
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
