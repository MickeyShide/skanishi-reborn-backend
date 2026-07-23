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


class TestItemRoutes:
    def test_get_item(self, client: TestClient) -> None:
        async def fake_get_item(self, current_user, item_id):
            from app.schemas.item import (
                CategoryResponse,
                ItemFullResponse,
                PrototypeResponse,
            )
            from app.schemas.item_type import ItemTypeResponse

            return ItemFullResponse(
                id=item_id,
                title="Test Item",
                number=1,
                type=ItemTypeResponse(
                    id=1,
                    title="ART",
                    description="Item type",
                    photo_url=None,
                ),
                category=CategoryResponse(
                    id=1,
                    title="Category",
                    color="#fff",
                    description="Category",
                ),
                prototype=PrototypeResponse(
                    id=1,
                    title="Prototype",
                    description="Prototype",
                    photo_url=None,
                    type_id=1,
                ),
            )

        with patch("app.api.v1.item.ItemsBusinessService.get_item", fake_get_item):
            response = client.get("/api/v1/items/1")

        assert response.status_code == 200
        assert response.json()["title"] == "Test Item"

    def test_get_item_rating(self, client: TestClient) -> None:
        async def fake_get_item_rating(self, current_user, item_id, params):
            from app.schemas.validation import ItemRatingResponse
            return ItemRatingResponse(
                items=[],
                meta={"limit": 100, "offset": 0, "total": 0},
            )

        with patch("app.api.v1.item.ItemsBusinessService.get_item_rating", fake_get_item_rating):
            response = client.get("/api/v1/items/1/rating")

        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["meta"]["total"] == 0
