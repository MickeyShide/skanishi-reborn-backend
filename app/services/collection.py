from app.db.models.collection import Collection, UserCollection
from app.db.repositories.collection import CollectionItemRow, CollectionRepository
from app.services.base import BaseService


class CollectionService(BaseService):
    repositories = {"collection_repository": CollectionRepository}

    collection_repository: CollectionRepository

    async def get_active_collections(self) -> list[Collection]:
        return await self.collection_repository.get_active_collections()

    async def get_items_for_collections(
        self,
        *,
        collection_ids: list[str],
    ) -> list[CollectionItemRow]:
        return await self.collection_repository.get_items_for_collections(
            collection_ids=collection_ids
        )

    async def get_user_collections(
        self,
        *,
        user_id: int,
        collection_ids: list[str],
    ) -> list[UserCollection]:
        return await self.collection_repository.get_user_collections(
            user_id=user_id,
            collection_ids=collection_ids,
        )

    async def get_user_collection(
        self,
        *,
        user_id: int,
        collection_id: str,
    ) -> UserCollection | None:
        return await self.collection_repository.get_user_collection(
            user_id=user_id,
            collection_id=collection_id,
        )

    async def get_user_item_ids(self, *, user_id: int) -> set[int]:
        return await self.collection_repository.get_user_item_ids(user_id=user_id)

    async def get_collection(self, collection_id: str) -> Collection | None:
        return await self.collection_repository.get(collection_id)

    async def mark_reward_claimed(self, user_collection: UserCollection) -> UserCollection:
        return await self.collection_repository.mark_reward_claimed(user_collection)
