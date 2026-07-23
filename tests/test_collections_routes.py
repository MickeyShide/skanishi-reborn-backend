from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.api.v1.dependencies import get_current_user


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role='user', tg_id=777)
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


class TestCollectionRoutes:
    def test_get_collections(self, client: TestClient) -> None:
        async def fake_get_user_collections(self, user):
            from app.services.business.collections import CollectionResponse
            return [
                CollectionResponse(
                    id="c1",
                    name="Test Collection",
                    description="Desc",
                    reward_xp=100,
                    reward_item_id=None,
                    is_active=True,
                    items=[],
                    progress_percent=50,
                    is_completed=False,
                    reward_claimed=False
                )
            ]

        with patch("app.api.v1.collection.CollectionBusinessService.get_user_collections", fake_get_user_collections):
            response = client.get("/api/v1/collections")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "c1"
        assert data[0]["name"] == "Test Collection"
        assert data[0]["progress_percent"] == 50

    def test_claim_collection_reward(self, client: TestClient) -> None:
        async def fake_claim_reward(self, user, collection_id):
            from app.services.business.collections import CollectionClaimResponse
            # Mock the user response which corresponds to CollectionClaimResponse (FrontendUserResponse fields)
            return CollectionClaimResponse(
                id="pub-id",
                display_name="User",
                username="user",
                rank=1,
                level=1,
                level_progress=50,
                xp=50,
                next_level_xp=100,
                streak_days=1,
                season_label="S1",
                coins=100,
            )

        with patch("app.api.v1.collection.CollectionBusinessService.claim_reward", fake_claim_reward):
            # CSRF protection dependency might be in place (e.g. enforce_csrf_protection).
            # For tests using the mocked client, we can either pass the expected header or mock the dependency if it fails.
            # Usually TestClient in this project doesn't have issues unless the CSRF depends on request.headers.
            # Let's override it just in case.
            from app.api.v1.dependencies import enforce_csrf_protection
            app.dependency_overrides[enforce_csrf_protection] = lambda: None
            
            response = client.post("/api/v1/collections/c1/claim")
            
            app.dependency_overrides.pop(enforce_csrf_protection, None)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "pub-id"
        assert data["xp"] == 50
