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


class TestReferralRoutes:
    def test_get_my_referrals(self, client: TestClient) -> None:
        stats = SimpleNamespace(
            referral_link="https://t.me/skanishi_bot/app?startapp=ref_1",
            total_friends=3,
            friends_list=["Alice", "bob_tg", "Charlie"],
        )
        with patch(
            "app.api.v1.referral.ReferralBusinessService.get_my_referrals",
            new=AsyncMock(return_value=stats),
        ):
            response = client.get("/api/v1/referrals/me")

        assert response.status_code == 200
        data = response.json()
        
        # Link should contain the user ID (1)
        assert "ref_1" in data["referral_link"]
        assert data["total_friends"] == 3
        # Should fallback correctly: first_name -> username -> "Охотник"
        assert data["friends_list"] == ["Alice", "bob_tg", "Charlie"]
