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


class TestDailyRoutes:
    def test_get_daily_status(self, client: TestClient) -> None:
        async def fake_get_daily_status(self, user):
            from app.services.business.daily_and_quests import DailyStatusResponse
            return DailyStatusResponse(
                is_available=True,
                reward_xp=50,
                streak_days=3,
            )

        with patch("app.api.v1.daily.DailyRewardBusinessService.get_daily_status", fake_get_daily_status):
            response = client.get("/api/v1/daily/status")

        assert response.status_code == 200
        data = response.json()
        assert data["is_available"] is True
        assert data["reward_xp"] == 50
        assert data["streak_days"] == 3

    def test_claim_daily_reward(self, client: TestClient) -> None:
        async def fake_claim_daily_reward(self, user):
            from app.services.business.daily_and_quests import DailyClaimResponse
            from app.schemas.frontend import FrontendUserResponse
            return DailyClaimResponse(
                reward_xp=50,
                streak_days=4,
                user=FrontendUserResponse(
                    id="pub-id",
                    display_name="User",
                    username="user",
                    rank=1,
                    level=1,
                    level_progress=50,
                    xp=50,
                    next_level_xp=100,
                    streak_days=4,
                    season_label="S1",
                    coins=100,
                )
            )

        with patch("app.api.v1.daily.DailyRewardBusinessService.claim_daily_reward", fake_claim_daily_reward):
            from app.api.v1.dependencies import enforce_csrf_protection
            app.dependency_overrides[enforce_csrf_protection] = lambda: None
            
            response = client.post("/api/v1/daily/claim")
            
            app.dependency_overrides.pop(enforce_csrf_protection, None)

        assert response.status_code == 200
        data = response.json()
        assert data["reward_xp"] == 50
        assert data["streak_days"] == 4
        assert data["user"]["id"] == "pub-id"
