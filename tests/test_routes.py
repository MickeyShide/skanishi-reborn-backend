from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_current_user
from app.api.v1 import auth as auth_api
from app.api.v1 import health as health_api
from app.config import settings
from app.db.models.user import UserRole
from app.main import app
from app.schemas.auth import TelegramAuthRequest, TokenResponse
from app.schemas.user import UserMe
from app.services.errors import (
    ExpiredInitDataError,
    ExpiredRefreshTokenError,
    InvalidInitDataError,
    InvalidRefreshTokenError,
    InvalidTelegramSignatureError,
    RefreshReuseDetectedError,
    RevokedRefreshTokenError,
    UserNotFoundError,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def build_user_me() -> UserMe:
    return UserMe(
        id=1,
        tg_id=777,
        first_name="Mickey",
        last_name="Shide",
        photo_url=None,
        is_private=True,
        username="mickey",
        is_premium=False,
        role=UserRole.USER,
    )


def build_token_response(access_token: str = "access-token") -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        expires_in=3600,
        user=build_user_me(),
    )


class TestHealthRoutes:
    def test_live_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health/live")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_ready_health_returns_ok_when_all_checks_pass(
        self,
        client: TestClient,
    ) -> None:
        async def check_ok() -> None:
            return None

        with (
            patch.object(health_api, "check_database", check_ok),
            patch.object(health_api, "check_redis", check_ok),
        ):
            response = client.get("/health/ready")

        assert response.status_code == 200
        assert response.json() == {
            "status": "ready",
            "db": "ok",
            "redis": "ok",
        }

    def test_ready_health_reports_database_failure(
        self,
        client: TestClient,
    ) -> None:
        async def check_database_failed() -> None:
            raise RuntimeError("database unavailable")

        async def check_redis_ok() -> None:
            return None

        with (
            patch.object(health_api, "check_database", check_database_failed),
            patch.object(health_api, "check_redis", check_redis_ok),
        ):
            response = client.get("/health/ready")

        assert response.status_code == 503
        assert response.json()["error"]["details"] == {
            "db": "failed",
            "redis": "ok",
        }

    def test_ready_health_reports_multiple_failures(
        self,
        client: TestClient,
    ) -> None:
        async def check_database_failed() -> None:
            raise RuntimeError("database unavailable")

        async def check_redis_failed() -> None:
            raise RuntimeError("redis unavailable")

        with (
            patch.object(health_api, "check_database", check_database_failed),
            patch.object(health_api, "check_redis", check_redis_failed),
        ):
            response = client.get("/health/ready")

        assert response.status_code == 503
        assert response.json()["error"]["details"] == {
            "db": "failed",
            "redis": "failed",
        }


class TestAuthInitRoute:
    def test_init_accepts_json_payload_and_sets_cookie(
        self,
        client: TestClient,
    ) -> None:
        expected_response = build_token_response()
        captured: dict[str, object] = {}

        async def fake_authenticate(self, dto, request, response):
            captured["dto"] = dto
            captured["content_type"] = request.headers.get("content-type")
            response.set_cookie("refresh_token", "refresh-token", path="/auth/refresh")
            return expected_response

        with patch.object(
            auth_api.AuthBusinessService,
            "authenticate",
            fake_authenticate,
        ):
            response = client.post(
                "/auth/init",
                json={"tg_web_app_data": "signed-init-data"},
            )

        assert response.status_code == 200
        assert response.json() == expected_response.model_dump(mode="json")
        assert isinstance(captured["dto"], TelegramAuthRequest)
        assert captured["dto"].tg_web_app_data == "signed-init-data"
        assert "application/json" in str(captured["content_type"])
        assert "refresh_token=refresh-token" in response.headers["set-cookie"]

    def test_init_accepts_form_payload(
        self,
        client: TestClient,
    ) -> None:
        captured: dict[str, object] = {}

        async def fake_authenticate(self, dto, request, response):
            captured["dto"] = dto
            return build_token_response()

        with patch.object(
            auth_api.AuthBusinessService,
            "authenticate",
            fake_authenticate,
        ):
            response = client.post(
                "/auth/init",
                data={"tg_web_app_data": "signed-init-data"},
            )

        assert response.status_code == 200
        assert captured["dto"].tg_web_app_data == "signed-init-data"

    def test_init_accepts_urlencoded_body_without_content_type(
        self,
        client: TestClient,
    ) -> None:
        captured: dict[str, object] = {}

        async def fake_authenticate(self, dto, request, response):
            captured["dto"] = dto
            return build_token_response()

        with patch.object(
            auth_api.AuthBusinessService,
            "authenticate",
            fake_authenticate,
        ):
            response = client.post(
                "/auth/init",
                content=b"tg_web_app_data=signed-init-data",
            )

        assert response.status_code == 200
        assert captured["dto"].tg_web_app_data == "signed-init-data"

    def test_init_rejects_missing_payload(
        self,
        client: TestClient,
    ) -> None:
        response = client.post("/auth/init", json={})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"

    def test_init_propagates_business_errors(
        self,
        client: TestClient,
    ) -> None:
        async def fake_authenticate(self, dto, request, response):
            raise InvalidInitDataError()

        with patch.object(
            auth_api.AuthBusinessService,
            "authenticate",
            fake_authenticate,
        ):
            response = client.post(
                "/auth/init",
                json={"tg_web_app_data": "bad-init-data"},
            )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_init_data"

    def test_init_propagates_invalid_telegram_signature(
        self,
        client: TestClient,
    ) -> None:
        async def fake_authenticate(self, dto, request, response):
            raise InvalidTelegramSignatureError()

        with patch.object(
            auth_api.AuthBusinessService,
            "authenticate",
            fake_authenticate,
        ):
            response = client.post(
                "/auth/init",
                json={"tg_web_app_data": "bad-signature"},
            )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "invalid_telegram_signature"

    def test_init_propagates_expired_init_data(
        self,
        client: TestClient,
    ) -> None:
        async def fake_authenticate(self, dto, request, response):
            raise ExpiredInitDataError()

        with patch.object(
            auth_api.AuthBusinessService,
            "authenticate",
            fake_authenticate,
        ):
            response = client.post(
                "/auth/init",
                json={"tg_web_app_data": "expired-init-data"},
            )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "expired_init_data"


class TestAuthRefreshRoute:
    def test_refresh_returns_rotated_tokens(
        self,
        client: TestClient,
    ) -> None:
        expected_response = build_token_response("rotated-access-token")
        captured = {}

        async def fake_refresh(self, request, response):
            captured["cookie"] = request.cookies.get("refresh_token")
            response.set_cookie(
                "refresh_token",
                "new-refresh-token",
                path="/auth/refresh",
            )
            return expected_response

        with patch.object(auth_api.AuthBusinessService, "refresh", fake_refresh):
            response = client.post(
                "/auth/refresh",
                cookies={"refresh_token": "old-refresh-token"},
            )

        assert response.status_code == 200
        assert response.json() == expected_response.model_dump(mode="json")
        assert captured["cookie"] == "old-refresh-token"
        assert "refresh_token=new-refresh-token" in response.headers["set-cookie"]
        assert "Path=/auth/refresh" in response.headers["set-cookie"]

    def test_refresh_requires_refresh_cookie(
        self,
        client: TestClient,
    ) -> None:
        response = client.post("/auth/refresh")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "missing_refresh_token"

    def test_refresh_propagates_service_errors(
        self,
        client: TestClient,
    ) -> None:
        async def fake_refresh(self, request, response):
            raise InvalidRefreshTokenError()

        with patch.object(auth_api.AuthBusinessService, "refresh", fake_refresh):
            response = client.post(
                "/auth/refresh",
                cookies={"refresh_token": "broken-token"},
            )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_refresh_token"

    @pytest.mark.parametrize(
        ("exc", "expected_status", "expected_code"),
        [
            (ExpiredRefreshTokenError(), 401, "expired_refresh_token"),
            (RevokedRefreshTokenError(), 401, "revoked_refresh_token"),
            (RefreshReuseDetectedError(), 403, "refresh_reuse_detected"),
        ],
    )
    def test_refresh_propagates_security_errors(
        self,
        client: TestClient,
        exc,
        expected_status: int,
        expected_code: str,
    ) -> None:
        async def fake_refresh(self, request, response):
            raise exc

        with patch.object(auth_api.AuthBusinessService, "refresh", fake_refresh):
            response = client.post(
                "/auth/refresh",
                cookies={"refresh_token": "broken-token"},
            )

        assert response.status_code == expected_status
        assert response.json()["error"]["code"] == expected_code

    def test_refresh_requires_csrf_header_when_samesite_none(
        self,
        client: TestClient,
    ) -> None:
        with patch.object(settings, "COOKIE_SAMESITE", "none"):
            response = client.post(
                "/auth/refresh",
                cookies={
                    "refresh_token": "refresh-token",
                    "csrf_token": "csrf-token",
                },
            )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    def test_refresh_accepts_matching_csrf_header_when_samesite_none(
        self,
        client: TestClient,
    ) -> None:
        async def fake_refresh(self, request, response):
            return build_token_response("csrf-safe-access-token")

        with (
            patch.object(settings, "COOKIE_SAMESITE", "none"),
            patch.object(auth_api.AuthBusinessService, "refresh", fake_refresh),
        ):
            response = client.post(
                "/auth/refresh",
                cookies={
                    "refresh_token": "refresh-token",
                    "csrf_token": "csrf-token",
                },
                headers={"X-CSRF-Token": "csrf-token"},
            )

        assert response.status_code == 200


class TestAuthLogoutRoute:
    def test_logout_revokes_session_and_returns_204(
        self,
        client: TestClient,
    ) -> None:
        fake_logout = AsyncMock(return_value=None)

        with patch.object(auth_api.AuthBusinessService, "logout", fake_logout):
            response = client.post(
                "/auth/logout",
                cookies={"refresh_token": "refresh-token"},
            )

        assert response.status_code == 204
        assert response.content == b""
        assert fake_logout.await_count == 1

    def test_logout_requires_csrf_header_when_samesite_none(
        self,
        client: TestClient,
    ) -> None:
        with patch.object(settings, "COOKIE_SAMESITE", "none"):
            response = client.post(
                "/auth/logout",
                cookies={
                    "refresh_token": "refresh-token",
                    "csrf_token": "csrf-token",
                },
            )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    def test_logout_without_cookie_is_idempotent(
        self,
        client: TestClient,
    ) -> None:
        response = client.post("/auth/logout")

        assert response.status_code == 204
        assert response.content == b""


class TestAuthMeRoute:
    def test_me_returns_current_user(
        self,
        client: TestClient,
    ) -> None:
        user = build_user_me()

        async def fake_current_user():
            return user

        app.dependency_overrides[get_current_user] = fake_current_user
        try:
            response = client.get(
                "/auth/me",
                headers={"Authorization": "Bearer access-token"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json() == user.model_dump(mode="json")

    def test_me_requires_authorization_header(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/auth/me")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "missing_authorization"

    def test_me_rejects_invalid_access_token(
        self,
        client: TestClient,
    ) -> None:
        response = client.get(
            "/auth/me",
            headers={"Authorization": "invalid"},
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_access_token"

    def test_me_returns_not_found_when_user_is_missing(
        self,
        client: TestClient,
    ) -> None:
        async def fake_current_user():
            raise UserNotFoundError()

        app.dependency_overrides[get_current_user] = fake_current_user
        try:
            response = client.get(
                "/auth/me",
                headers={"Authorization": "Bearer access-token"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "user_not_found"
