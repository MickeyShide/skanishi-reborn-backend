from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import auth as auth_api
from app.api.v1 import health as health_api
from app.api.v1 import item as item_api
from app.api.v1 import map as map_api
from app.api.v1 import profile as profile_api
from app.api.v1 import user as user_api
from app.api.v1.dependencies import get_current_user
from app.config import settings
from app.db.models.user import UserRole
from app.main import app
from app.schemas.auth import TelegramAuthRequest, TokenResponse
from app.schemas.item import (
    CategoryResponse,
    ItemFullResponse,
    ItemsResponse,
    MyItemsResponse,
    PrototypeResponse,
)
from app.schemas.item_type import ItemTypeResponse
from app.schemas.profile import ValidationCountResponse
from app.schemas.user import (
    UserMe,
    UserPrivacySettingsResponse,
    UserPrivacySettingsUpdateRequest,
)
from app.schemas.validation import (
    ItemRatingResponse,
    RatingEntryResponse,
    ValidationResponse,
    ValidationShortResponse,
)
from app.services.business.items import ItemsBusinessService
from app.services.business.profile import ProfileBusinessService
from app.services.business.user import UserBusinessService
from app.services.errors import (
    ExpiredInitDataError,
    ExpiredRefreshTokenError,
    InvalidInitDataError,
    InvalidRefreshTokenError,
    InvalidTelegramSignatureError,
    ItemNotCollectedError,
    RefreshReuseDetectedError,
    RevokedRefreshTokenError,
    UserNotFoundError,
)
from app.services.token import TokenService


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


def build_access_token(role: UserRole = UserRole.USER) -> str:
    user = build_user_me()
    user.role = role
    return TokenService().create_access_token(user)


def build_item_type_response() -> ItemTypeResponse:
    return ItemTypeResponse(
        id=10,
        title="Artifact",
        description="Rare type",
        photo_url="https://example.com/type.png",
    )


def build_category_response() -> CategoryResponse:
    return CategoryResponse(
        id=11,
        title="Museum",
        color="#112233",
        description="Museum items",
    )


def build_prototype_response() -> PrototypeResponse:
    return PrototypeResponse(
        id=12,
        title="Prototype",
        description="Prototype description",
        photo_url="https://example.com/prototype.png",
        type_id=10,
    )


def build_item_full_response(
    item_id: int = 1,
    *,
    title: str = "Known item",
    number: int = 7,
) -> ItemFullResponse:
    return ItemFullResponse(
        id=item_id,
        title=title,
        number=number,
        type=build_item_type_response(),
        category=build_category_response(),
        prototype=build_prototype_response(),
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


class TestItemRoutes:
    def test_items_returns_paginated_catalog(
        self,
        client: TestClient,
    ) -> None:
        captured = {}
        expected_response = ItemsResponse(
            items=[build_item_full_response()],
            meta={"limit": 100, "offset": 0, "total": 1},
        )

        async def fake_get_items(self, params):
            captured["params"] = params
            return expected_response

        with patch.object(ItemsBusinessService, "get_items", fake_get_items):
            response = client.get(
                "/items",
                headers={"Authorization": f"Bearer {build_access_token()}"},
                params={"limit": 50, "offset": 10, "category_id": 3, "type_id": 4},
            )

        assert response.status_code == 200
        assert response.json() == expected_response.model_dump(mode="json")
        assert captured["params"].limit == 50
        assert captured["params"].offset == 10
        assert captured["params"].category_id == 3
        assert captured["params"].type_id == 4

    def test_items_requires_authorization_header(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/items")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "missing_authorization"

    def test_my_items_returns_hidden_and_collected_entries(
        self,
        client: TestClient,
    ) -> None:
        hidden_item = {
            "state": "hidden",
            "id": 1,
            "title": None,
            "number": None,
            "type": build_item_type_response().model_dump(mode="json"),
            "category": build_category_response().model_dump(mode="json"),
            "prototype": build_prototype_response().model_dump(mode="json"),
        }
        collected_item = build_item_full_response(item_id=2, number=2)
        expected_response = MyItemsResponse(
            items=[hidden_item, collected_item],
            meta={"limit": 100, "offset": 0, "total": 2},
        )

        async def fake_get_my_items(self, params):
            return expected_response

        with patch.object(ItemsBusinessService, "get_my_items", fake_get_my_items):
            response = client.get(
                "/items/my",
                headers={"Authorization": f"Bearer {build_access_token()}"},
            )

        assert response.status_code == 200
        assert response.json() == expected_response.model_dump(mode="json")

    def test_get_item_returns_union_response(
        self,
        client: TestClient,
    ) -> None:
        expected_response = build_item_full_response(item_id=2, number=2)

        async def fake_get_item(self, item_id):
            assert item_id == 2
            return expected_response

        with patch.object(ItemsBusinessService, "get_item", fake_get_item):
            response = client.get(
                "/items/2",
                headers={"Authorization": f"Bearer {build_access_token()}"},
            )

        assert response.status_code == 200
        assert response.json() == expected_response.model_dump(mode="json")

    def test_get_full_item_propagates_item_not_collected(
        self,
        client: TestClient,
    ) -> None:
        async def fake_get_full_item(self, item_id):
            raise ItemNotCollectedError()

        with patch.object(ItemsBusinessService, "get_full_item", fake_get_full_item):
            response = client.get(
                "/items/2/full",
                headers={"Authorization": f"Bearer {build_access_token()}"},
            )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "item_not_collected"

    def test_get_item_rating_returns_paginated_payload(
        self,
        client: TestClient,
    ) -> None:
        expected_response = ItemRatingResponse(
            items=[
                RatingEntryResponse(
                    rank=1,
                    created_at="2026-06-29T06:00:00Z",
                    user=None,
                )
            ],
            meta={"limit": 100, "offset": 0, "total": 1},
        )

        async def fake_get_item_rating(self, item_id, params):
            assert item_id == 2
            assert params.limit == 100
            return expected_response

        with patch.object(
            ItemsBusinessService, "get_item_rating", fake_get_item_rating
        ):
            response = client.get(
                "/items/2/rating",
                headers={"Authorization": f"Bearer {build_access_token()}"},
            )

        assert response.status_code == 200
        assert response.json() == expected_response.model_dump(mode="json")

    def test_collect_item_by_secret_returns_validation_response(
        self,
        client: TestClient,
    ) -> None:
        token = "abc.def.ghijklmnop"
        expected_response = ValidationResponse(
            status="created",
            validation=ValidationShortResponse(
                id=5,
                item_id=2,
                rank=1,
                created_at="2026-06-29T06:00:00Z",
            ),
            item=build_item_full_response(item_id=2, number=2),
        )

        async def fake_collect_item_by_secret(self, dto):
            assert dto.token == token
            return expected_response

        with patch.object(
            ItemsBusinessService,
            "collect_item_by_secret",
            fake_collect_item_by_secret,
        ):
            response = client.post(
                "/items/secret",
                headers={"Authorization": f"Bearer {build_access_token()}"},
                json={"token": token},
            )

        assert response.status_code == 200
        assert response.json() == expected_response.model_dump(mode="json")


class TestMapRuntimeRoutes:
    def test_map_api_key_returns_public_browser_key(
        self,
        client: TestClient,
    ) -> None:
        with patch.object(settings, "YANDEX_MAPS_API_KEY", "yandex-browser-key"):
            response = client.get("/map/api-key")

        assert response.status_code == 200
        assert response.json() == {"api_key": "yandex-browser-key"}

    def test_map_api_key_returns_503_when_not_configured(
        self,
        client: TestClient,
    ) -> None:
        with patch.object(settings, "YANDEX_MAPS_API_KEY", None):
            response = client.get("/map/api-key")

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "map_api_key_not_configured"

    def test_map_api_key_does_not_require_authorization(
        self,
        client: TestClient,
    ) -> None:
        with patch.object(settings, "YANDEX_MAPS_API_KEY", "yandex-browser-key"):
            response = client.get("/map/api-key")

        assert response.status_code == 200
        assert "api_key" in response.json()


class TestProfileRoutes:
    def test_validation_count_returns_count(
        self,
        client: TestClient,
    ) -> None:
        expected_response = ValidationCountResponse(count=12)

        async def fake_get_validation_count(self):
            return expected_response

        with patch.object(
            ProfileBusinessService,
            "get_validation_count",
            fake_get_validation_count,
        ):
            response = client.get(
                "/profile/validations/count",
                headers={"Authorization": f"Bearer {build_access_token()}"},
            )

        assert response.status_code == 200
        assert response.json() == expected_response.model_dump(mode="json")

    def test_validation_count_requires_authorization_header(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/profile/validations/count")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "missing_authorization"


class TestUserPrivacyRoutes:
    def test_get_privacy_settings_returns_value(
        self,
        client: TestClient,
    ) -> None:
        expected_response = UserPrivacySettingsResponse(privacy=True)

        async def fake_get_privacy_settings(self):
            return expected_response

        with patch.object(
            UserBusinessService,
            "get_privacy_settings",
            fake_get_privacy_settings,
        ):
            response = client.get(
                "/users/settings/privacy",
                headers={"Authorization": f"Bearer {build_access_token()}"},
            )

        assert response.status_code == 200
        assert response.json() == expected_response.model_dump(mode="json")

    def test_patch_privacy_settings_returns_updated_value(
        self,
        client: TestClient,
    ) -> None:
        expected_response = UserPrivacySettingsResponse(privacy=False)
        captured = {}

        async def fake_update_privacy_settings(self, dto):
            captured["dto"] = dto
            return expected_response

        with patch.object(
            UserBusinessService,
            "update_privacy_settings",
            fake_update_privacy_settings,
        ):
            response = client.patch(
                "/users/settings/privacy",
                headers={"Authorization": f"Bearer {build_access_token()}"},
                json={"privacy": False},
            )

        assert response.status_code == 200
        assert response.json() == expected_response.model_dump(mode="json")
        assert isinstance(captured["dto"], UserPrivacySettingsUpdateRequest)
        assert captured["dto"].privacy is False

    def test_user_privacy_routes_require_authorization_header(
        self,
        client: TestClient,
    ) -> None:
        get_response = client.get("/users/settings/privacy")
        patch_response = client.patch(
            "/users/settings/privacy",
            json={"privacy": False},
        )

        assert get_response.status_code == 401
        assert get_response.json()["error"]["code"] == "missing_authorization"
        assert patch_response.status_code == 401
        assert patch_response.json()["error"]["code"] == "missing_authorization"


class TestItemRouteContracts:
    def test_items_router_is_registered(self) -> None:
        response = TestClient(app, raise_server_exceptions=False).get("/items")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "missing_authorization"

    def test_items_handlers_do_not_expose_session_dependency(self) -> None:
        import inspect

        for handler in [
            item_api.get_items,
            item_api.get_my_items,
            item_api.get_item,
            item_api.get_full_item,
            item_api.get_item_rating,
            item_api.collect_item_by_secret,
        ]:
            parameters = inspect.signature(handler).parameters
            assert "session" not in parameters
            assert "service" not in parameters


class TestProfileRouteContracts:
    def test_profile_router_is_registered(self) -> None:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/profile/validations/count"
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "missing_authorization"

    def test_profile_handler_does_not_expose_session_dependency(self) -> None:
        import inspect

        parameters = inspect.signature(profile_api.get_validation_count).parameters
        assert "session" not in parameters
        assert "service" not in parameters


class TestMapRouteContracts:
    def test_map_runtime_handler_does_not_expose_session_dependency(self) -> None:
        import inspect

        parameters = inspect.signature(map_api.get_map_api_key).parameters
        assert "session" not in parameters
        assert "service" not in parameters


class TestUserRouteContracts:
    def test_user_router_is_registered(self) -> None:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/users/settings/privacy"
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "missing_authorization"

    def test_user_handlers_do_not_expose_session_dependency(self) -> None:
        import inspect

        for handler in [
            user_api.get_privacy_settings,
            user_api.update_privacy_settings,
        ]:
            parameters = inspect.signature(handler).parameters
            assert "session" not in parameters
            assert "service" not in parameters
