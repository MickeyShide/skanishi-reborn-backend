from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from app.db.models.shop import ShopItemType
from app.services.business.shop import ShopBusinessService
from app.services.errors import InsufficientCoinsError, InsufficientFragmentsError


def build_item(
    item_id: int = 1,
    *,
    item_type: ShopItemType = ShopItemType.BORDER,
    price: int = 100,
    fragment_cost: int | None = None,
    fragment_rarity: str | None = None,
):
    return SimpleNamespace(
        id=item_id,
        name="Item",
        item_type=item_type,
        price=price,
        asset_url="asset",
        fragment_cost=fragment_cost,
        fragment_rarity=fragment_rarity,
        is_active=True,
    )


class ShopBusinessServiceTests(IsolatedAsyncioTestCase):
    def make_service(self) -> ShopBusinessService:
        service = object.__new__(ShopBusinessService)
        service.shop_service = MagicMock()
        service.user_service = MagicMock()
        service.shop_service.get_active_items = AsyncMock()
        service.shop_service.get_owned_item_ids = AsyncMock()
        service.shop_service.get_active_item = AsyncMock()
        service.shop_service.get_item = AsyncMock()
        service.shop_service.is_owned = AsyncMock()
        service.shop_service.grant_item = AsyncMock()
        service.user_service.update_fields = AsyncMock()
        return service

    async def test_get_shop_items_maps_ownership_and_equipment(self) -> None:
        service = self.make_service()
        user = SimpleNamespace(id=1, active_border_id=1, active_bg_id=None)
        service.shop_service.get_active_items.return_value = [
            build_item(1),
            build_item(2, item_type=ShopItemType.BACKGROUND),
            build_item(3),
        ]
        service.shop_service.get_owned_item_ids.return_value = {1, 2}

        result = await service.get_shop_items(user)

        self.assertEqual([(item.is_owned, item.is_equipped) for item in result], [(True, True), (True, False), (False, False)])

    async def test_buy_item_deducts_coins_and_grants_cosmetic(self) -> None:
        service = self.make_service()
        user = SimpleNamespace(id=1, coins=150)
        service.shop_service.get_active_item.return_value = build_item()
        service.shop_service.is_owned.return_value = False

        result = await service.buy_item(user, 1)

        self.assertTrue(result.is_owned)
        service.user_service.update_fields.assert_awaited_once_with(user, coins=50)
        service.shop_service.grant_item.assert_awaited_once_with(user_id=1, item_id=1)

    async def test_buy_item_rejects_insufficient_coins(self) -> None:
        service = self.make_service()
        service.shop_service.get_active_item.return_value = build_item(price=100)
        service.shop_service.is_owned.return_value = False

        with self.assertRaises(InsufficientCoinsError):
            await service.buy_item(SimpleNamespace(id=1, coins=50), 1)

    async def test_craft_item_debits_fragments_and_grants_cosmetic(self) -> None:
        service = self.make_service()
        user = SimpleNamespace(id=1, fragments_rare=50)
        service.shop_service.get_active_item.return_value = build_item(
            fragment_cost=20,
            fragment_rarity="RARE",
        )
        service.shop_service.is_owned.return_value = False

        result = await service.craft_item(user, 1)

        self.assertTrue(result.is_owned)
        service.user_service.update_fields.assert_awaited_once_with(
            user,
            fragments_rare=30,
        )
        service.shop_service.grant_item.assert_awaited_once_with(user_id=1, item_id=1)

    async def test_craft_item_rejects_insufficient_fragments(self) -> None:
        service = self.make_service()
        service.shop_service.get_active_item.return_value = build_item(
            fragment_cost=20,
            fragment_rarity="RARE",
        )
        service.shop_service.is_owned.return_value = False

        with self.assertRaises(InsufficientFragmentsError):
            await service.craft_item(SimpleNamespace(id=1, fragments_rare=10), 1)

    async def test_equip_item_updates_active_field(self) -> None:
        service = self.make_service()
        user = SimpleNamespace(id=1, active_border_id=None, active_bg_id=None)
        service.shop_service.get_item.return_value = build_item(9)
        service.shop_service.is_owned.return_value = True

        result = await service.equip_item(user, 9)

        self.assertTrue(result.is_equipped)
        service.user_service.update_fields.assert_awaited_once_with(
            user,
            active_border_id=9,
        )
