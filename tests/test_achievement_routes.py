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


class TestAchievementRoutes:
    def test_get_achievements(self, client: TestClient) -> None:
        async def fake_get_achievements(self, current_user):
            from app.schemas.frontend import AchievementsResponse
            return AchievementsResponse(
                total_earned=1,
                items=[]
            )

        with patch("app.api.v1.achievement.FrontendDataBusinessService.get_achievements", fake_get_achievements):
            response = client.get("/api/v1/achievements")

        assert response.status_code == 200
        data = response.json()
        assert data["total_earned"] == 1
        assert "items" in data
