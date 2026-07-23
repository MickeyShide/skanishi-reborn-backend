from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, UTC

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.api.v1.dependencies import get_current_user


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role='user', tg_id=777)
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


class TestEventsRoutes:
    def test_get_events(self, client: TestClient) -> None:
        async def fake_get_active_events(self, user):
            from app.services.business.events import EventDetailResponse
            return [
                EventDetailResponse(
                    id="e1",
                    title="Test Event",
                    rarity="epic",
                    xp_multiplier="1.5",
                    starts_at=datetime.now(UTC),
                    ends_at=datetime.now(UTC),
                    is_active=True,
                    modifiers=[],
                    items=[],
                    goals=[]
                )
            ]

        with patch("app.api.v1.events.EventBusinessService.get_active_events", fake_get_active_events):
            response = client.get("/api/v1/events")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "e1"
        assert data[0]["title"] == "Test Event"

    def test_claim_goal_reward(self, client: TestClient) -> None:
        async def fake_claim_goal_reward(self, user, event_id, goal_id):
            from app.schemas.frontend import FrontendUserResponse
            return FrontendUserResponse(
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

        with patch("app.api.v1.events.EventBusinessService.claim_goal_reward", fake_claim_goal_reward):
            from app.api.v1.dependencies import enforce_csrf_protection
            app.dependency_overrides[enforce_csrf_protection] = lambda: None
            
            response = client.post("/api/v1/events/e1/goals/g1/claim")
            
            app.dependency_overrides.pop(enforce_csrf_protection, None)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "pub-id"
        assert data["xp"] == 50
