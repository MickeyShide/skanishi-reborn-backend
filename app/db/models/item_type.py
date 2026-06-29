from sqlalchemy import Index
from sqlmodel import Field, String, Text

from app.db.models.base import BaseSQLModel


class ItemType(BaseSQLModel, table=True):
    __tablename__ = "types"
    __table_args__ = (Index("ux_types_title", "title", unique=True),)

    title: str = Field(sa_type=String(128), nullable=False)
    description: str = Field(
        default="",
        sa_type=Text,
        nullable=False,
        sa_column_kwargs={"server_default": ""},
    )
    photo_url: str | None = Field(default=None, sa_type=Text, nullable=True)
