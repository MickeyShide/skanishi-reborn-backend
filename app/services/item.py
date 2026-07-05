from app.db.models.item import Item
from app.db.repositories.item import ItemCatalogRow, ItemRepository
from app.services.base import BaseService


class ItemService(BaseService):
    repositories = {
        "item_repository": ItemRepository,
    }

    item_repository: ItemRepository

    async def get_active_catalog_page(
        self,
        *,
        limit: int,
        offset: int,
        category_id: int | None = None,
        type_id: int | None = None,
    ) -> list[ItemCatalogRow]:
        return await self.item_repository.get_active_catalog_page(
            limit=limit,
            offset=offset,
            category_id=category_id,
            type_id=type_id,
        )

    async def count_active_catalog(
        self,
        *,
        category_id: int | None = None,
        type_id: int | None = None,
    ) -> int:
        return await self.item_repository.count_active_catalog(
            category_id=category_id,
            type_id=type_id,
        )

    async def get_active_catalog_item(self, item_id: int) -> ItemCatalogRow | None:
        return await self.item_repository.get_active_catalog_item(item_id)

    async def get_active_item_by_id(self, item_id: int) -> Item | None:
        return await self.item_repository.get_active_item_by_id(item_id)

    async def get_active_item_for_update(self, item_id: int) -> Item | None:
        return await self.item_repository.get_active_item_for_update(item_id)

    async def increment_validation_count(self, item: Item) -> Item:
        return await self.item_repository.update(
            item,
            validation_count=item.validation_count + 1,
        )

