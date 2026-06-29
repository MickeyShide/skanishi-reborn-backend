from sqlalchemy import CheckConstraint, Index
from sqlmodel import Field, String, Text

from app.db.models.base import BaseSQLModel


class Category(BaseSQLModel, table=True):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint(
            "color ~ '^#[0-9A-Fa-f]{6}$' "
            "OR color IN ("
            "'primary', 'secondary', 'success', 'warning', "
            "'danger', 'info', 'neutral'"
            ")",
            name="ck_categories_color",
        ),
        Index("ux_categories_title", "title", unique=True),
    )

    title: str = Field(sa_type=String(128), nullable=False)
    color: str = Field(sa_type=String(32), nullable=False)
    description: str = Field(
        default="",
        sa_type=Text,
        nullable=False,
        sa_column_kwargs={"server_default": ""},
    )
