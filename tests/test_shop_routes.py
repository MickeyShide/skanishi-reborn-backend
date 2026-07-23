from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.api.v1.dependencies import get_current_user


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role='user', tg_id=777)
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


class TestShopRoutes:
    def test_get_shop_items(self, client: TestClient) -> None:
        async def fake_get_shop_items(self, user):
            from app.schemas.shop import ShopItemResponse
            from app.db.models.shop import ShopItemType
            return [
                ShopItemResponse(
                    id=1,
                    name="Cool Border",
                    item_type=ShopItemType.BORDER,
                    price=100,
                    asset_url="url",
                    fragment_cost=0,
                    fragment_rarity=None,
                    is_owned=True,
                    is_equipped=True
                )
            ]

        with patch("app.api.v1.shop.ShopBusinessService.get_shop_items", fake_get_shop_items):
            response = client.get("/api/v1/shop")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["item_type"] == "BORDER"
        assert data[0]["is_owned"] is True

    def test_buy_shop_item(self, client: TestClient) -> None:
        async def fake_buy_item(self, user, item_id):
            from app.schemas.shop import ShopItemResponse
            from app.db.models.shop import ShopItemType
            return ShopItemResponse(
                id=item_id,
                name="Bought Border",
                item_type=ShopItemType.BORDER,
                price=100,
                asset_url="url",
                fragment_cost=0,
                fragment_rarity=None,
                is_owned=True,
                is_equipped=False
            )

        with patch("app.api.v1.shop.ShopBusinessService.buy_item", fake_buy_item):
            response = client.post("/api/v1/shop/2/buy")

        assert response.status_code == 200
        assert response.json()["id"] == 2
        assert response.json()["is_owned"] is True

    def test_equip_shop_item(self, client: TestClient) -> None:
        async def fake_equip_item(self, user, item_id):
            from app.schemas.shop import ShopItemResponse
            from app.db.models.shop import ShopItemType
            return ShopItemResponse(
                id=item_id,
                name="Equipped Border",
                item_type=ShopItemType.BORDER,
                price=100,
                asset_url="url",
                fragment_cost=0,
                fragment_rarity=None,
                is_owned=True,
                is_equipped=True
            )

        with patch("app.api.v1.shop.ShopBusinessService.equip_item", fake_equip_item):
            response = client.post("/api/v1/shop/2/equip")

        assert response.status_code == 200
        assert response.json()["id"] == 2
        assert response.json()["is_equipped"] is True

    def test_craft_shop_item(self, client: TestClient) -> None:
        async def fake_craft_item(self, user, item_id):
            from app.schemas.shop import ShopItemResponse
            from app.db.models.shop import ShopItemType
            return ShopItemResponse(
                id=item_id,
                name="Crafted Border",
                item_type=ShopItemType.BORDER,
                price=100,
                asset_url="url",
                fragment_cost=50,
                fragment_rarity="RARE",
                is_owned=True,
                is_equipped=False
            )

        with patch("app.api.v1.shop.ShopBusinessService.craft_item", fake_craft_item):
            response = client.post("/api/v1/shop/3/craft")

        assert response.status_code == 200
        assert response.json()["id"] == 3
        assert response.json()["is_owned"] is True
        assert response.json()["fragment_cost"] == 50
