from enum import StrEnum
from sqlalchemy import BigInteger, String, UniqueConstraint
from sqlmodel import Field
from app.db.models.base import BaseSQLModel

class ShopItemType(StrEnum):
    BORDER = "BORDER"
    BACKGROUND = "BACKGROUND"
    TITLE = "TITLE"

class ShopItem(BaseSQLModel, table=True):
    __tablename__ = "shop_items"

    name: str = Field(sa_type=String(255), nullable=False)
    item_type: str = Field(sa_type=String(64), nullable=False) # border, background, title
    price: int = Field(default=0, nullable=False)
    is_active: bool = Field(
        default=True,
        nullable=False,
        sa_column_kwargs={"server_default": "true"},
    )
    asset_url: str | None = Field(default=None, sa_type=String(1024), nullable=True)
    fragment_cost: int | None = Field(default=None, nullable=True)
    fragment_rarity: str | None = Field(default=None, sa_type=String(32), nullable=True)


class UserCosmetic(BaseSQLModel, table=True):
    __tablename__ = "user_cosmetics"

    user_id: int = Field(
        foreign_key="users.id",
        nullable=False,
        sa_type=BigInteger,
    )
    shop_item_id: int = Field(
        foreign_key="shop_items.id",
        nullable=False,
        sa_type=BigInteger,
    )
    
    __table_args__ = (
        UniqueConstraint("user_id", "shop_item_id", name="uq_user_shop_item"),
    )
