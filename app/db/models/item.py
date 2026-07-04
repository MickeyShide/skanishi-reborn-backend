from sqlalchemy import BigInteger, CheckConstraint, Column, ForeignKey, Index, text
from sqlmodel import Field, String

from app.db.models.base import BaseSQLModel


class Item(BaseSQLModel, table=True):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("number > 0", name="ck_items_number_positive"),
        CheckConstraint(
            "validation_count >= 0",
            name="ck_items_validation_count_non_negative",
        ),
        Index("ux_items_number", "number", unique=True),
        Index("ix_items_category_id", "category_id"),
        Index("ix_items_prototype_id", "prototype_id"),
        Index("ix_items_type_id", "type_id"),
        Index("ix_items_is_active", "is_active"),
        Index("ix_items_category_type", "category_id", "type_id"),
    )

    title: str = Field(sa_type=String(128), nullable=False)
    number: int = Field(nullable=False)
    prototype_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("prototypes.id", name="fk_items_prototype_id_prototypes"),
            nullable=False,
        ),
    )
    category_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("categories.id", name="fk_items_category_id_categories"),
            nullable=False,
        ),
    )
    type_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("types.id", name="fk_items_type_id_types"),
            nullable=False,
        ),
    )
    validation_count: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )
    is_active: bool = Field(
        default=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("true")},
    )
