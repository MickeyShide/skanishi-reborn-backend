from sqlalchemy import select

from app.db.models.shop import ShopItem, UserCosmetic
from app.db.repositories.base import BaseRepository


class ShopItemRepository(BaseRepository[ShopItem]):
    model = ShopItem

    async def get_active_items(self) -> list[ShopItem]:
        result = await self.session.execute(
            select(ShopItem).where(ShopItem.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def get_active_by_id(self, item_id: int) -> ShopItem | None:
        result = await self.session.execute(
            select(ShopItem)
            .where(ShopItem.id == item_id, ShopItem.is_active.is_(True))
            .limit(1)
        )
        return result.scalar_one_or_none()


class UserCosmeticRepository(BaseRepository[UserCosmetic]):
    model = UserCosmetic

    async def get_owned_item_ids(self, *, user_id: int) -> set[int]:
        result = await self.session.execute(
            select(UserCosmetic.shop_item_id).where(UserCosmetic.user_id == user_id)
        )
        return set(result.scalars().all())

    async def get_by_user_and_item(
        self,
        *,
        user_id: int,
        item_id: int,
    ) -> UserCosmetic | None:
        result = await self.session.execute(
            select(UserCosmetic)
            .where(
                UserCosmetic.user_id == user_id,
                UserCosmetic.shop_item_id == item_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
