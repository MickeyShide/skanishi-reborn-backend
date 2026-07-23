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


class TestProfileRoutes:
    def test_get_profile(self, client: TestClient) -> None:
        async def fake_get_profile(self, current_user):
            from app.schemas.frontend import ProfileResponse, FrontendUserResponse
            return ProfileResponse(
                user=FrontendUserResponse(
                    id="pub-id",
                    display_name="User",
                    username="user",
                    rank=1,
                    level=1,
                    level_progress=50,
                    xp=100,
                    next_level_xp=200,
                    streak_days=1,
                    season_label="S1",
                    coins=100,
                ),
                total_collections=5,
                completed_collections=1,
            )

        with patch("app.api.v1.profile.ProfileBusinessService.get_profile", fake_get_profile):
            response = client.get("/api/v1/profile")

        assert response.status_code == 200
        assert response.json()["user"]["xp"] == 100

    def test_get_me(self, client: TestClient) -> None:
        async def fake_get_me(self, current_user):
            from app.schemas.frontend import FrontendUserResponse
            return FrontendUserResponse(
                id="pub-id",
                display_name="Me",
                username="me",
                rank=1,
                level=1,
                level_progress=50,
                xp=500,
                next_level_xp=1000,
                streak_days=1,
                season_label="S1",
                coins=100,
            )

        with patch("app.api.v1.user.UserBusinessService.get_me", fake_get_me):
            response = client.get("/api/v1/users/me")

        assert response.status_code == 200
        assert response.json()["xp"] == 500
