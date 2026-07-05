from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.v1 import health
from app.main import app


class HealthTests(TestCase):
    def test_live_health(self) -> None:
        response = TestClient(app).get("/api/v1/health/live")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_ready_health(self) -> None:
        async def check_ok() -> None:
            return None

        with (
            patch.object(health, "check_database", check_ok),
            patch.object(health, "check_redis", check_ok),
        ):
            response = TestClient(app).get("/api/v1/health/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ready",
                "db": "ok",
                "redis": "ok",
            },
        )

    def test_ready_health_error_format(self) -> None:
        async def check_ok() -> None:
            return None

        async def check_failed() -> None:
            raise RuntimeError("redis unavailable")

        with (
            patch.object(health, "check_database", check_ok),
            patch.object(health, "check_redis", check_failed),
        ):
            response = TestClient(app).get("/api/v1/health/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "service_not_ready")
        self.assertEqual(
            response.json()["error"]["details"],
            {
                "db": "ok",
                "redis": "failed",
            },
        )
