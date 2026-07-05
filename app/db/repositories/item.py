from sqlalchemy import func, select

from app.db.models.category import Category
from app.db.models.item import Item
from app.db.models.item_type import ItemType
from app.db.models.prototype import Prototype
from app.db.repositories.base import BaseRepository

type ItemCatalogRow = tuple[Item, Category, Prototype, ItemType]


class ItemRepository(BaseRepository[Item]):
    model = Item

    @staticmethod
    def _apply_catalog_filters(
        query,
        *,
        category_id: int | None = None,
        type_id: int | None = None,
        item_id: int | None = None,
    ):
        if category_id is not None:
            query = query.where(Item.category_id == category_id)

        if type_id is not None:
            query = query.where(Item.type_id == type_id)

        if item_id is not None:
            query = query.where(Item.id == item_id)

        return query

    def _catalog_query(self):
        return (
            select(Item, Category, Prototype, ItemType)
            .join(Category, Category.id == Item.category_id)
            .join(Prototype, Prototype.id == Item.prototype_id)
            .join(ItemType, ItemType.id == Item.type_id)
            .where(Item.is_active.is_(True))
        )

    async def get_active_catalog_page(
        self,
        *,
        limit: int,
        offset: int,
        category_id: int | None = None,
        type_id: int | None = None,
    ) -> list[ItemCatalogRow]:
        query = self._apply_catalog_filters(
            self._catalog_query(),
            category_id=category_id,
            type_id=type_id,
        ).order_by(Item.number.asc(), Item.id.asc())
        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)

        return list(result.all())

    async def count_active_catalog(
        self,
        *,
        category_id: int | None = None,
        type_id: int | None = None,
    ) -> int:
        query = self._apply_catalog_filters(
            select(func.count())
            .select_from(Item)
            .where(Item.is_active.is_(True)),
            category_id=category_id,
            type_id=type_id,
        )

        result = await self.session.execute(query)

        return int(result.scalar_one())

    async def get_active_catalog_item(self, item_id: int) -> ItemCatalogRow | None:
        query = self._apply_catalog_filters(
            self._catalog_query(),
            item_id=item_id,
        ).limit(1)

        result = await self.session.execute(query)

        return result.first()

    async def get_active_item_by_id(self, item_id: int) -> Item | None:
        query = (
            select(Item)
            .where(
                Item.id == item_id,
                Item.is_active.is_(True),
            )
            .limit(1)
        )

        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    async def get_active_item_for_update(self, item_id: int) -> Item | None:
        query = (
            select(Item)
            .where(
                Item.id == item_id,
                Item.is_active.is_(True),
            )
            .with_for_update()
            .limit(1)
        )

        result = await self.session.execute(query)

        return result.scalar_one_or_none()
