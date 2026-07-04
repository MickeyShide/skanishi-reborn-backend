from sqlalchemy import BigInteger, Column, ForeignKey, Index
from sqlmodel import Field, String, Text

from app.db.models.base import BaseSQLModel


class Prototype(BaseSQLModel, table=True):
    __tablename__ = "prototypes"
    __table_args__ = (Index("ix_prototypes_type_id", "type_id"),)

    title: str = Field(sa_type=String(128), nullable=False)
    description: str = Field(
        default="",
        sa_type=Text,
        nullable=False,
        sa_column_kwargs={"server_default": ""},
    )
    photo_url: str | None = Field(default=None, sa_type=Text, nullable=True)
    type_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("types.id", name="fk_prototypes_type_id_types"),
            nullable=False,
        ),
    )
