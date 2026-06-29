from sqlalchemy import BigInteger, Column, ForeignKey, Index, text
from sqlmodel import Field, Text

from app.db.models.base import BaseSQLModel


class ItemImage(BaseSQLModel, table=True):
    __tablename__ = "item_images"
    __table_args__ = (
        Index("ix_item_images_item_id", "item_id"),
        Index(
            "ux_item_images_one_main_per_item",
            "item_id",
            unique=True,
            postgresql_where=text("is_main = true"),
        ),
    )

    item_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("items.id"),
            nullable=False,
        ),
    )
    url: str = Field(sa_type=Text, nullable=False)
    is_main: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": text("false")},
    )
    position: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )
