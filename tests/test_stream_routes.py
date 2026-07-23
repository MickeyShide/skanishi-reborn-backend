from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.api.v1.dependencies import get_current_user, get_stream_user


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role='user', tg_id=777)
    app.dependency_overrides[get_stream_user] = lambda: SimpleNamespace(id=1, role='user', tg_id=777)
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


class TestStreamRoutes:
    def test_sse_stream(self, client: TestClient) -> None:
        async def fake_sse_generator(request, user_id):
            yield {"data": "test_message"}

        with patch("app.api.v1.stream.event_generator", fake_sse_generator):
            response = client.get("/api/v1/stream/events?token=test-token")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "data: test_message" in response.text
