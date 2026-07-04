from sqlalchemy import BigInteger, CheckConstraint, Column, ForeignKey
from sqlmodel import Field, Index

from app.db.models.base import BaseSQLModel


class Validation(BaseSQLModel, table=True):
    __tablename__ = "validations"

    user_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "users.id",
                ondelete="CASCADE",
                name="fk_validations_user_id_users",
            ),
            nullable=False,
        ),
    )

    item_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "items.id",
                ondelete="CASCADE",
                name="fk_validations_item_id_items",
            ),
            nullable=False,
        ),
    )

    item_secret_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "item_secrets.id",
                ondelete="RESTRICT",
                name="fk_validations_item_secret_id_item_secrets",
            ),
            nullable=False,
        ),
    )

    rank: int = Field(nullable=False)

    __table_args__ = (
        Index("ux_validations_user_item", "user_id", "item_id", unique=True),
        Index("ux_validations_item_rank", "item_id", "rank", unique=True),
        CheckConstraint("rank > 0", name="ck_validations_rank_positive"),
        Index("ix_validations_user_id", "user_id"),
        Index("ix_validations_item_id", "item_id"),
        Index("ix_validations_item_secret_id", "item_secret_id"),
        Index("ix_validations_item_created_at", "item_id", "created_at", "id"),
    )
