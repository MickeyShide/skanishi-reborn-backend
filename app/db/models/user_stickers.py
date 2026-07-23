from sqlalchemy import BigInteger, Column, ForeignKey, Index, String, UniqueConstraint, text
from sqlmodel import Field

from app.db.models.base import BaseSQLModel


class UserSticker(BaseSQLModel, table=True):
    __tablename__ = "user_stickers"

    user_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True, # MVP: 1 sticker per user
        ),
    )
    token: str = Field(
        sa_type=String(64),
        nullable=False,
    )
    scan_count: int = Field(default=0, nullable=False, sa_column_kwargs={"server_default": "0"})
    total_passive_xp: int = Field(default=0, nullable=False, sa_column_kwargs={"server_default": "0"})
    total_passive_coins: int = Field(default=0, nullable=False, sa_column_kwargs={"server_default": "0"})
    
    is_active: bool = Field(
        default=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("true")},
    )

    __table_args__ = (
        Index("ux_user_stickers_token", "token", unique=True),
    )


class UserStickerScan(BaseSQLModel, table=True):
    __tablename__ = "user_sticker_scans"

    user_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    sticker_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("user_stickers.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )

    __table_args__ = (
        UniqueConstraint("user_id", "sticker_id", name="ux_user_sticker_scans_user_sticker"),
        Index("ix_user_sticker_scans_sticker_id", "sticker_id"),
    )
