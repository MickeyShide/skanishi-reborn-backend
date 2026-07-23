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


class TestQuestsRoutes:
    def test_get_user_quests(self, client: TestClient) -> None:
        async def fake_get_user_quests(self, user):
            from app.schemas.frontend import QuestCardResponse, QuestsResponse
            return QuestsResponse(
                items=[
                    QuestCardResponse(
                    id="q1",
                    title="Find Items",
                    description="Find 5 items",
                    reward_xp=100,
                    reward_item_id=None,
                    target_count=5,
                    current_progress=2,
                    is_completed=False,
                    reward_claimed=False,
                    )
                ]
            )

        with patch("app.api.v1.quest.FrontendDataBusinessService.get_quests", fake_get_user_quests):
            response = client.get("/api/v1/quests")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == "q1"
        assert data["items"][0]["current_progress"] == 2

    def test_claim_quest_reward(self, client: TestClient) -> None:
        async def fake_claim_quest_reward(self, user, quest_id):
            from app.services.business.daily_and_quests import DailyClaimResponse
            from app.schemas.frontend import FrontendUserResponse
            return DailyClaimResponse(
                reward_xp=100,
                streak_days=1,
                user=FrontendUserResponse(
                    id="pub-id",
                    display_name="User",
                    username="user",
                    rank=1,
                    level=1,
                    level_progress=50,
                    xp=150,
                    next_level_xp=200,
                    streak_days=1,
                    season_label="S1",
                    coins=100,
                )
            )

        with patch("app.api.v1.quest.UserQuestBusinessService.claim_quest_reward", fake_claim_quest_reward):
            from app.api.v1.dependencies import enforce_csrf_protection
            app.dependency_overrides[enforce_csrf_protection] = lambda: None
            
            response = client.post("/api/v1/quests/q1/claim")
            
            app.dependency_overrides.pop(enforce_csrf_protection, None)

        assert response.status_code == 200
        data = response.json()
        assert data["reward_xp"] == 100
        assert data["user"]["xp"] == 150
