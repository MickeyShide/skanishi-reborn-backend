from sqlalchemy import select

from app.db.models.collection import Collection, CollectionItem, UserCollection
from app.db.models.item import Item
from app.db.models.validation import Validation
from app.db.repositories.base import BaseRepository

type CollectionItemRow = tuple[CollectionItem, Item]


class CollectionRepository(BaseRepository[Collection]):
    model = Collection

    async def get_active_collections(self) -> list[Collection]:
        result = await self.session.execute(
            select(Collection).where(Collection.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def get_items_for_collections(
        self,
        *,
        collection_ids: list[str],
    ) -> list[CollectionItemRow]:
        if not collection_ids:
            return []
        result = await self.session.execute(
            select(CollectionItem, Item)
            .join(Item, Item.id == CollectionItem.item_id)
            .where(CollectionItem.collection_id.in_(collection_ids))
        )
        return list(result.all())

    async def get_user_collections(
        self,
        *,
        user_id: int,
        collection_ids: list[str],
    ) -> list[UserCollection]:
        if not collection_ids:
            return []
        result = await self.session.execute(
            select(UserCollection).where(
                UserCollection.user_id == user_id,
                UserCollection.collection_id.in_(collection_ids),
            )
        )
        return list(result.scalars().all())

    async def get_user_collection(
        self,
        *,
        user_id: int,
        collection_id: str,
    ) -> UserCollection | None:
        result = await self.session.execute(
            select(UserCollection)
            .where(
                UserCollection.user_id == user_id,
                UserCollection.collection_id == collection_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_user_item_ids(self, *, user_id: int) -> set[int]:
        result = await self.session.execute(
            select(Validation.item_id).where(Validation.user_id == user_id)
        )
        return set(result.scalars().all())

    async def mark_reward_claimed(self, user_collection: UserCollection) -> UserCollection:
        return await self.update(user_collection, reward_claimed=True)
