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


class TestMiscRoutes:
    def test_get_app_state(self, client: TestClient) -> None:
        async def fake_get_state(self, current_user):
            from app.schemas.frontend import FrontendAppStateResponse
            return FrontendAppStateResponse.model_construct(
                user={}, quests=[], recentRewards=[], mapPins=[], nearbyPoints=[],
                pointDetails=[], stats=[], profileLinks=[], xpHistoryGroups=[],
                achievements=[], achievementSummary={}, activeEvent=None,
            )

        with patch("app.api.v1.app_state.FrontendDataBusinessService.get_app_state", fake_get_state):
            response = client.get("/api/v1/app/state")

        assert response.status_code == 200
        assert response.json()["quests"] == []

    def test_get_xp_history(self, client: TestClient) -> None:
        async def fake_get_xp_history(self, current_user, params):
            from app.schemas.frontend import XpHistoryResponse, XpWeekSummaryResponse
            return XpHistoryResponse(
                groups=[],
                weekly=XpWeekSummaryResponse(total=100, days=[100, 0, 0, 0, 0, 0, 0]),
            )

        with patch("app.api.v1.xp.FrontendDataBusinessService.get_xp_history", fake_get_xp_history):
            response = client.get("/api/v1/xp/history?limit=10&offset=0")

        assert response.status_code == 200
        assert response.json()["groups"] == []
        assert response.json()["weekly"]["total"] == 100
