from datetime import datetime

from sqlalchemy import CHAR, BigInteger, Column, DateTime, ForeignKey, String, text
from sqlmodel import Field, Index

from app.db.models.base import BaseSQLModel


class ItemSecret(BaseSQLModel, table=True):
    __tablename__ = "item_secrets"

    item_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "items.id",
                ondelete="CASCADE",
                name="fk_item_secrets_item_id_items",
            ),
            nullable=False,
        ),
    )

    secret_hash: str = Field(
        sa_type=CHAR(64),
        nullable=False,
    )

    title: str = Field(sa_type=String(128), nullable=False)
    coords: str | None = Field(default=None, sa_type=String(128), nullable=True)
    is_active: bool = Field(
        default=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("true")},
    )

    expires_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ux_item_secrets_secret_hash", "secret_hash", unique=True),
        Index("ix_item_secrets_item_id", "item_id"),
        Index("ix_item_secrets_active", "is_active"),
    )
