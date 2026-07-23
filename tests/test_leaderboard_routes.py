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


class TestLeaderboardRoutes:
    def test_get_leaderboard(self, client: TestClient) -> None:
        async def fake_get_top_users(self, limit, offset):
            from app.schemas.frontend import FrontendUserResponse
            return [
                FrontendUserResponse(
                    id="pub-id-1",
                    display_name="Top User 1",
                    username="top_user_1",
                    rank=1,
                    level=10,
                    level_progress=50,
                    xp=1000,
                    next_level_xp=2000,
                    streak_days=10,
                    season_label="S1",
                    coins=100,
                ),
                FrontendUserResponse(
                    id="pub-id-2",
                    display_name="Top User 2",
                    username="top_user_2",
                    rank=2,
                    level=9,
                    level_progress=20,
                    xp=900,
                    next_level_xp=1000,
                    streak_days=5,
                    season_label="S1",
                    coins=50,
                )
            ]

        with patch("app.api.v1.leaderboard.LeaderboardBusinessService.get_top_users", fake_get_top_users):
            response = client.get("/api/v1/leaderboard?limit=2&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["rank"] == 1
        assert data[1]["rank"] == 2
        assert data[0]["username"] == "top_user_1"
