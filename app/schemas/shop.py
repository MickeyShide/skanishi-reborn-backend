from pydantic import BaseModel

class ShopItemResponse(BaseModel):
    id: int
    name: str
    item_type: str
    price: int
    asset_url: str | None = None
    is_owned: bool
    is_equipped: bool

class BuyItemRequest(BaseModel):
    item_id: int

class EquipItemRequest(BaseModel):
    item_id: int
