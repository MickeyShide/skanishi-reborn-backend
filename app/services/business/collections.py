from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict

from app.db.models.enums import UIColorToken
from app.db.models.user import User
from app.schemas.frontend import FrontendUserResponse
from app.services.business.base import BusinessService
from app.services.business.daily_and_quests import _build_user_response
from app.services.collection import CollectionService
from app.services.errors import ForbiddenError, ItemNotFoundError, RewardAlreadyClaimedError
from app.services.user import UserService
from app.services.xp_event import XpEventService


class CollectionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    number: int
    prototype_id: int
    category_id: int
    type_id: int
    validation_count: int
    is_active: bool
    is_acquired: bool = False


class CollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str = ""
    reward_xp: int = 0
    reward_item_id: int | None = None
    is_active: bool = True
    items: list[CollectionItemResponse] = []
    progress_percent: int = 0
    is_completed: bool = False
    reward_claimed: bool = False


class CollectionClaimResponse(FrontendUserResponse):
    pass


class CollectionBusinessService(BusinessService):
    """Business scenarios for retrieving and claiming collections."""

    collection_service: CollectionService
    user_service: UserService
    xp_event_service: XpEventService

    async def get_user_collections(self, current_user: User) -> list[CollectionResponse]:
        collections = await self.collection_service.get_active_collections()
        if not collections:
            return []

        collection_ids = [collection.id for collection in collections]
        collection_items = await self.collection_service.get_items_for_collections(
            collection_ids=collection_ids
        )
        items_by_collection: dict[str, list] = {}
        for collection_item, item in collection_items:
            items_by_collection.setdefault(collection_item.collection_id, []).append(item)

        user_collections = await self.collection_service.get_user_collections(
            user_id=current_user.id,
            collection_ids=collection_ids,
        )
        user_collection_by_id = {
            collection.collection_id: collection for collection in user_collections
        }
        acquired_item_ids = await self.collection_service.get_user_item_ids(
            user_id=current_user.id
        )

        responses: list[CollectionResponse] = []
        for collection in collections:
            required_items = items_by_collection.get(collection.id, [])
            total_required = len(required_items)
            mapped_items = [
                CollectionItemResponse(
                    **item.model_dump(),
                    is_acquired=item.id in acquired_item_ids,
                )
                for item in required_items
            ]
            acquired_count = sum(item.is_acquired for item in mapped_items)
            user_collection = user_collection_by_id.get(collection.id)
            is_completed = bool(
                user_collection is not None and user_collection.completed_at is not None
            )

            responses.append(
                CollectionResponse(
                    **collection.model_dump(),
                    items=mapped_items,
                    progress_percent=(
                        100
                        if is_completed
                        else int(acquired_count / total_required * 100)
                        if total_required
                        else 0
                    ),
                    is_completed=is_completed,
                    reward_claimed=(
                        user_collection.reward_claimed if user_collection else False
                    ),
                )
            )

        return responses

    async def claim_reward(
        self,
        current_user: User,
        collection_id: str,
    ) -> CollectionClaimResponse:
        user_collection = await self.collection_service.get_user_collection(
            user_id=current_user.id,
            collection_id=collection_id,
        )
        if user_collection is None or user_collection.completed_at is None:
            raise ForbiddenError("Collection is not completed yet.")
        if user_collection.reward_claimed:
            raise RewardAlreadyClaimedError("Collection reward already claimed.")

        collection = await self.collection_service.get_collection(collection_id)
        if collection is None:
            raise ItemNotFoundError("Collection not found.")

        xp = collection.reward_xp
        source = f"collection_claim:{current_user.id}:{collection.id}"
        existing_event = await self.xp_event_service.get_user_event_by_source(
            user_id=current_user.id,
            source=source,
        )

        updated_user = current_user
        if existing_event is None and xp > 0:
            await self.xp_event_service.create_event(
                user_id=current_user.id,
                xp=xp,
                source=source,
                tag="collection",
                color=UIColorToken.GOLD,
                occurred_at=datetime.now(UTC),
            )
            updated_user = await self.user_service.add_xp_and_check_level_up(
                current_user,
                xp,
            )

        await self.collection_service.mark_reward_claimed(user_collection)
        return CollectionClaimResponse(
            **_build_user_response(updated_user).model_dump()
        )
