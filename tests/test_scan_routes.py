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


class TestScanRoutes:
    def test_claim_scan_reward(self, client: TestClient) -> None:
        async def fake_claim_scan_reward(self, current_user, dto):
            from app.schemas.frontend import ScanClaimResponse, FrontendUserResponse
            return ScanClaimResponse(
                scanned_items=[],
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
                )
            )

        with patch("app.api.v1.scan.FrontendDataBusinessService.claim_scan_reward", fake_claim_scan_reward):
            from app.api.v1.dependencies import enforce_csrf_protection
            app.dependency_overrides[enforce_csrf_protection] = lambda: None
            
            response = client.post(
                "/api/v1/scan/claim",
                json={
                    "event_id": "test-event",
                    "latitude": 55.75,
                    "longitude": 37.61,
                    "item_tags": ["tag1", "tag2"]
                }
            )
            
            app.dependency_overrides.pop(enforce_csrf_protection, None)

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["xp"] == 100
        assert "scanned_items" in data
