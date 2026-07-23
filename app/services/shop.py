from __future__ import annotations

from app.db.models.shop import ShopItem, UserCosmetic
from app.db.repositories.shop import ShopItemRepository, UserCosmeticRepository
from app.services.base import BaseService


class ShopService(BaseService):
    repositories = {
        "shop_item_repository": ShopItemRepository,
        "user_cosmetic_repository": UserCosmeticRepository,
    }

    shop_item_repository: ShopItemRepository
    user_cosmetic_repository: UserCosmeticRepository

    async def get_active_items(self) -> list[ShopItem]:
        return await self.shop_item_repository.get_active_items()

    async def get_active_item(self, item_id: int) -> ShopItem | None:
        return await self.shop_item_repository.get_active_by_id(item_id)

    async def get_item(self, item_id: int) -> ShopItem | None:
        return await self.shop_item_repository.get(item_id)

    async def get_owned_item_ids(self, *, user_id: int) -> set[int]:
        return await self.user_cosmetic_repository.get_owned_item_ids(user_id=user_id)

    async def is_owned(self, *, user_id: int, item_id: int) -> bool:
        cosmetic = await self.user_cosmetic_repository.get_by_user_and_item(
            user_id=user_id,
            item_id=item_id,
        )
        return cosmetic is not None

    async def grant_item(self, *, user_id: int, item_id: int) -> UserCosmetic:
        return await self.user_cosmetic_repository.create(
            user_id=user_id,
            shop_item_id=item_id,
        )
