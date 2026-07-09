from __future__ import annotations

from sqlalchemy import select

from app.db.models.collection import Collection, CollectionItem, UserCollection
from app.db.models.item import Item
from app.db.models.user import User
from app.db.models.validation import Validation
from app.schemas.frontend import FrontendUserResponse
from app.services.business.base import BusinessService
from app.services.business.daily_and_quests import _build_user_response
from app.services.user import UserService


class CollectionItemResponse(Item):
    is_acquired: bool = False


class CollectionResponse(Collection):
    items: list[CollectionItemResponse] = []
    progress_percent: int = 0
    is_completed: bool = False
    reward_claimed: bool = False


class CollectionClaimResponse(FrontendUserResponse):
    pass


class CollectionBusinessService(BusinessService):
    """Business service for retrieving and claiming collections."""

    user_service: UserService

    async def get_user_collections(self, current_user: User) -> list[CollectionResponse]:
        """Return all active collections with the user's current progress and items."""
        session = await self._get_session()

        # 1. Fetch active collections
        col_result = await session.execute(
            select(Collection).where(Collection.is_active.is_(True))
        )
        collections = list(col_result.scalars().all())
        if not collections:
            return []
            
        collection_ids = [c.id for c in collections]

        # 2. Fetch required items for these collections
        ci_result = await session.execute(
            select(CollectionItem, Item)
            .join(Item, Item.id == CollectionItem.item_id)
            .where(CollectionItem.collection_id.in_(collection_ids))
        )
        items_by_collection: dict[str, list[Item]] = {}
        for ci, item in ci_result.all():
            items_by_collection.setdefault(ci.collection_id, []).append(item)

        # 3. Fetch user's completion status for these collections
        uc_result = await session.execute(
            select(UserCollection).where(
                UserCollection.user_id == current_user.id,
                UserCollection.collection_id.in_(collection_ids),
            )
        )
        uc_by_collection: dict[str, UserCollection] = {
            uc.collection_id: uc for uc in uc_result.scalars().all()
        }

        # 4. Fetch the specific items the user has acquired
        # (Could optimise to only fetch IDs of items part of collections, but getting all is fine for now)
        val_result = await session.execute(
            select(Validation.item_id).where(Validation.user_id == current_user.id)
        )
        user_item_ids = set(val_result.scalars().all())

        # 5. Assemble response
        responses: list[CollectionResponse] = []
        for c in collections:
            req_items = items_by_collection.get(c.id, [])
            total_req = len(req_items)
            
            # Map required items to their acquired status
            mapped_items = []
            acquired_count = 0
            for item in req_items:
                acquired = item.id in user_item_ids
                if acquired:
                    acquired_count += 1
                mapped_items.append(
                    CollectionItemResponse(
                        **item.model_dump(),
                        is_acquired=acquired,
                    )
                )

            uc = uc_by_collection.get(c.id)
            is_completed = uc is not None and uc.completed_at is not None
            reward_claimed = uc.reward_claimed if uc else False
            
            # Progress calculation
            progress = 100 if is_completed else (
                int((acquired_count / total_req) * 100) if total_req > 0 else 0
            )

            response = CollectionResponse(
                **c.model_dump(),
                items=mapped_items,
                progress_percent=progress,
                is_completed=is_completed,
                reward_claimed=reward_claimed,
            )
            responses.append(response)

        return responses

    async def claim_reward(self, current_user: User, collection_id: str) -> CollectionClaimResponse:
        """Claim the XP reward for a fully completed collection."""
        from datetime import UTC, datetime

        from app.db.models.enums import UIColorToken
        from app.db.models.xp_event import XpEvent
        from app.services.errors import ForbiddenError, ItemNotFoundError, RewardAlreadyClaimedError
        
        session = await self._get_session()

        # 1. Fetch UserCollection
        uc_result = await session.execute(
            select(UserCollection).where(
                UserCollection.user_id == current_user.id,
                UserCollection.collection_id == collection_id,
            )
        )
        uc = uc_result.scalar_one_or_none()

        if not uc or not uc.completed_at:
            raise ForbiddenError("Collection is not completed yet.")

        if uc.reward_claimed:
            raise RewardAlreadyClaimedError("Collection reward already claimed.")

        # 2. Fetch Collection to get reward details
        collection = await session.get(Collection, collection_id)
        if not collection:
            raise ItemNotFoundError("Collection not found.")

        # 3. Grant XP (The background worker might have granted it automatically during migration, 
        # but to be safe, we check if the xp event already exists, or just rely on this manual claim flow.
        # Given the previous logic in game_tasks, the background worker *already* created the XpEvent.
        # Wait, if the worker already granted the XP when it hit 100%, what does claim do?
        # Let's adjust so the user manually claims it here instead of the background worker giving XP directly,
        # OR the claim button just marks it as claimed and acknowledges it, granting an extra bonus?
        # Standard approach: worker marks `completed_at=now`. 
        # Manual claim grants the XP event and sets `reward_claimed=True`.
        # Let's ensure we only grant XP once. We'll use a specific source string for the manual claim.)
        
        xp = collection.reward_xp
        source = f"collection_claim:{current_user.id}:{collection.id}"

        # Check idempotency
        existing = (
            await session.execute(
                select(XpEvent).where(
                    XpEvent.user_id == current_user.id,
                    XpEvent.source == source,
                ).limit(1)
            )
        ).scalar_one_or_none()

        updated_user = current_user
        if not existing and xp > 0:
            xp_event = XpEvent(
                user_id=current_user.id,
                xp=xp,
                source=source,
                tag="collection",
                color=UIColorToken.GOLD,
                occurred_at=datetime.now(UTC),
            )
            session.add(xp_event)
            
            user_svc = UserService(session)
            updated_user = await user_svc.add_xp_and_check_level_up(current_user, xp)

        uc.reward_claimed = True
        session.add(uc)
        
        # We rely on the router's Dependency injection or BusinessService auto-commit to commit this transaction.
        return CollectionClaimResponse(**_build_user_response(updated_user).model_dump())
