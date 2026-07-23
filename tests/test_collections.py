from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from app.services.business.collections import CollectionBusinessService
from app.services.errors import ForbiddenError, RewardAlreadyClaimedError


def build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=1, display_name="Test", first_name="Test", username="test", public_id="pub",
        rank=1, level=1, level_progress=0, xp=0, next_level_xp=1000,
        streak_days=1, season_label="S", coins=0, active_border_id=None, active_bg_id=None,
    )


class CollectionBusinessServiceTests(IsolatedAsyncioTestCase):
    def make_service(self) -> CollectionBusinessService:
        service = object.__new__(CollectionBusinessService)
        service.collection_service = MagicMock()
        service.collection_service.get_active_collections = AsyncMock()
        service.collection_service.get_items_for_collections = AsyncMock()
        service.collection_service.get_user_collections = AsyncMock()
        service.collection_service.get_user_item_ids = AsyncMock()
        service.collection_service.get_user_collection = AsyncMock()
        service.collection_service.get_collection = AsyncMock()
        service.collection_service.mark_reward_claimed = AsyncMock()
        service.user_service = MagicMock()
        service.user_service.add_xp_and_check_level_up = AsyncMock()
        service.xp_event_service = MagicMock()
        service.xp_event_service.get_user_event_by_source = AsyncMock()
        service.xp_event_service.create_event = AsyncMock()
        return service

    async def test_get_user_collections_maps_progress(self) -> None:
        service = self.make_service()
        collection = SimpleNamespace(
            id="c1", name="C1", description="desc", reward_xp=100,
            reward_item_id=None, is_active=True,
            model_dump=lambda: {"id": "c1", "name": "C1", "description": "desc", "reward_xp": 100, "reward_item_id": None, "is_active": True},
        )
        item = SimpleNamespace(
            id=10, title="Item", number=1, prototype_id=1, category_id=1, type_id=1,
            validation_count=1, is_active=True,
            model_dump=lambda: {"id": 10, "title": "Item", "number": 1, "prototype_id": 1, "category_id": 1, "type_id": 1, "validation_count": 1, "is_active": True},
        )
        item_two = SimpleNamespace(**{**item.__dict__, "id": 11})
        item_two.model_dump = lambda: {**item.model_dump(), "id": 11}
        service.collection_service.get_active_collections.return_value = [collection]
        service.collection_service.get_items_for_collections.return_value = [
            (SimpleNamespace(collection_id="c1"), item),
            (SimpleNamespace(collection_id="c1"), item_two),
        ]
        service.collection_service.get_user_collections.return_value = []
        service.collection_service.get_user_item_ids.return_value = {10}

        result = await service.get_user_collections(SimpleNamespace(id=1))

        self.assertEqual(result[0].progress_percent, 50)
        self.assertEqual([item.is_acquired for item in result[0].items], [True, False])

    async def test_claim_reward_rejects_uncompleted_collection(self) -> None:
        service = self.make_service()
        service.collection_service.get_user_collection.return_value = SimpleNamespace(
            completed_at=None,
            reward_claimed=False,
        )

        with self.assertRaises(ForbiddenError):
            await service.claim_reward(SimpleNamespace(id=1), "c1")

    async def test_claim_reward_rejects_duplicate_claim(self) -> None:
        service = self.make_service()
        service.collection_service.get_user_collection.return_value = SimpleNamespace(
            completed_at=object(),
            reward_claimed=True,
        )

        with self.assertRaises(RewardAlreadyClaimedError):
            await service.claim_reward(SimpleNamespace(id=1), "c1")

    async def test_claim_reward_creates_event_and_marks_claimed(self) -> None:
        service = self.make_service()
        user = build_user()
        user_collection = SimpleNamespace(completed_at=object(), reward_claimed=False)
        service.collection_service.get_user_collection.return_value = user_collection
        service.collection_service.get_collection.return_value = SimpleNamespace(
            id="c1",
            reward_xp=100,
        )
        service.xp_event_service.get_user_event_by_source.return_value = None
        service.user_service.add_xp_and_check_level_up.return_value = user

        result = await service.claim_reward(user, "c1")

        self.assertEqual(result.id, "pub")
        service.xp_event_service.create_event.assert_awaited_once()
        service.collection_service.mark_reward_claimed.assert_awaited_once_with(user_collection)
