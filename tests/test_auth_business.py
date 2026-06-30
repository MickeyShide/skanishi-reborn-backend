import inspect
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock

import jwt
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.responses import Response

from app.api.v1 import auth as auth_api
from app.config import settings
from app.db.models.user import UserRole
from app.main import app
from app.schemas.auth import (
    AccessTokenClaims,
    RefreshTokenClaims,
    TelegramAuthRequest,
)
from app.services.business.auth import AuthBusinessService
from app.services.init_data import TelegramUserData
from app.services.token import TokenService
from app.services.user import UserService


def build_user() -> SimpleNamespace:
    return SimpleNamespace(
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


class AuthBusinessServiceScenarioTests(IsolatedAsyncioTestCase):
    async def test_authenticate_orchestrates_auth_flow_and_returns_token_response(
        self,
    ) -> None:
        service = object.__new__(AuthBusinessService)
        telegram_user = TelegramUserData(
            tg_id=777,
            first_name="Mickey",
            last_name="Shide",
            username="mickey",
            language_code="ru",
            is_premium=False,
            photo_url=None,
        )
        telegram_init_data = SimpleNamespace(user=telegram_user)
        user = build_user()

        service.telegram_init_data_service = MagicMock()
        service.telegram_init_data_service.validate_and_parse.return_value = (
            telegram_init_data
        )
        service.init_data_replay_guard_service = MagicMock()
        service.init_data_replay_guard_service.ensure_not_replayed = AsyncMock()
        service.user_service = MagicMock()
        service.user_service.get_or_create_from_telegram = AsyncMock(return_value=user)
        service.token_service = MagicMock()
        service.token_service.create_access_token.return_value = "access-token"
        service.token_service.create_refresh_token.return_value = "refresh-token"
        service.refresh_session_service = MagicMock()
        service.refresh_session_service.create_refresh_session = AsyncMock()

        dto = TelegramAuthRequest(tg_web_app_data="signed-init-data")
        request = SimpleNamespace(
            headers={"user-agent": "unit-test-agent"},
            client=SimpleNamespace(host="127.0.0.1"),
        )
        response = Response()

        result = await AuthBusinessService.authenticate(
            service,
            dto=dto,
            request=request,
            response=response,
        )

        service.telegram_init_data_service.validate_and_parse.assert_called_once_with(
            "signed-init-data"
        )
        service.init_data_replay_guard_service.ensure_not_replayed.assert_awaited_once_with(
            "signed-init-data"
        )
        service.user_service.get_or_create_from_telegram.assert_awaited_once_with(
            telegram_user
        )
        service.token_service.create_access_token.assert_called_once_with(user)
        service.token_service.create_refresh_token.assert_called_once_with(user)
        service.refresh_session_service.create_refresh_session.assert_awaited_once_with(
            user_id=1,
            refresh_token="refresh-token",
            user_agent="unit-test-agent",
            ip_address="127.0.0.1",
        )
        self.assertEqual(result.access_token, "access-token")
        self.assertEqual(result.expires_in, settings.ACCESS_TOKEN_TTL_SECONDS)
        self.assertEqual(result.user.id, 1)
        self.assertEqual(result.user.tg_id, 777)
        self.assertIn("refresh_token=refresh-token", response.headers["set-cookie"])


class AuthEndpointContractTests(TestCase):
    def test_auth_init_route_is_registered_in_application(self) -> None:
        response = TestClient(app, raise_server_exceptions=False).post("/auth/init")

        self.assertEqual(
            response.status_code,
            422,
            "Если endpoint подключен, запрос без обязательного body должен "
            "валидироваться как 422, а не пропадать с 404.",
        )

    def test_auth_init_handler_exposes_session_dependency(self) -> None:
        parameters = inspect.signature(auth_api.auth_init).parameters

        self.assertIn(
            "session",
            parameters,
            "Хендлеру нужен доступ к AsyncSession, иначе AuthBusinessService "
            "нельзя корректно создать как instance service.",
        )

    def test_auth_refresh_requires_refresh_cookie(self) -> None:
        response = TestClient(app, raise_server_exceptions=False).post("/auth/refresh")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "missing_refresh_token")

    def test_auth_me_requires_authorization_header(self) -> None:
        response = TestClient(app, raise_server_exceptions=False).get("/auth/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "missing_authorization")


class AuthBusinessServiceConstructionTests(TestCase):
    def test_auth_business_service_can_be_constructed_with_session(self) -> None:
        try:
            service = AuthBusinessService(session=object())
        except TypeError as exc:
            self.fail(
                "Конструктор AuthBusinessService не должен падать на wiring "
                "зависимостей: "
                f"{exc}"
            )

        self.assertTrue(hasattr(service, "telegram_init_data_service"))
        self.assertTrue(hasattr(service, "token_service"))


class UserServiceTelegramMappingTests(IsolatedAsyncioTestCase):
    async def test_create_from_telegram_maps_last_name_to_repository(self) -> None:
        service = UserService(session=object())
        service.user_repository = MagicMock()
        service.user_repository.create = AsyncMock(return_value=build_user())

        telegram_user = TelegramUserData(
            tg_id=777,
            first_name="Mickey",
            last_name="Shide",
            username="mickey",
            language_code="ru",
            is_premium=True,
            photo_url="https://example.com/avatar.png",
        )

        await service.create_from_telegram(telegram_user)

        self.assertEqual(service.user_repository.create.await_count, 1)
        kwargs = service.user_repository.create.await_args.kwargs
        self.assertEqual(kwargs["last_name"], "Shide")

    async def test_update_telegram_fields_maps_last_name_to_repository(self) -> None:
        service = UserService(session=object())
        service.user_repository = MagicMock()
        service.user_repository.update = AsyncMock(return_value=build_user())
        user = build_user()
        telegram_user = TelegramUserData(
            tg_id=777,
            first_name="Mickey",
            last_name="Shide",
            username="mickey",
            language_code="ru",
            is_premium=False,
            photo_url=None,
        )

        await service.update_telegram_fields(user, telegram_user)

        self.assertEqual(service.user_repository.update.await_count, 1)
        kwargs = service.user_repository.update.await_args.kwargs
        self.assertEqual(kwargs["last_name"], "Shide")


class AuthBusinessServiceRefreshTests(IsolatedAsyncioTestCase):
    async def test_refresh_rotates_session_and_returns_token_response(self) -> None:
        service = object.__new__(AuthBusinessService)
        user = build_user()
        old_refresh_session = SimpleNamespace(id=10, user_id=1)
        new_refresh_session = SimpleNamespace(id=11)

        service.token_service = MagicMock()
        service.token_service.decode_refresh_token.return_value = SimpleNamespace(
            sub="1"
        )
        service.token_service.create_access_token.return_value = "new-access-token"
        service.token_service.create_refresh_token.return_value = "new-refresh-token"
        service.refresh_session_service = MagicMock()
        service.refresh_session_service.get_session_for_refresh = AsyncMock(
            return_value=old_refresh_session
        )
        service.refresh_session_service.create_refresh_session = AsyncMock(
            return_value=new_refresh_session
        )
        service.refresh_session_service.revoke_refresh_session = AsyncMock()
        service.user_service = MagicMock()
        service.user_service.get_user_by_id = AsyncMock(return_value=user)

        request = SimpleNamespace(
            headers={"user-agent": "refresh-agent"},
            cookies={"refresh_token": "old-refresh-token"},
            client=SimpleNamespace(host="127.0.0.1"),
        )

        response = Response()

        result = await AuthBusinessService.refresh(
            service,
            request=request,
            response=response,
        )

        service.refresh_session_service.get_session_for_refresh.assert_awaited_once_with(
            "old-refresh-token"
        )
        service.refresh_session_service.create_refresh_session.assert_awaited_once_with(
            user_id=1,
            refresh_token="new-refresh-token",
            user_agent="refresh-agent",
            ip_address="127.0.0.1",
        )
        service.refresh_session_service.revoke_refresh_session.assert_awaited_once_with(
            old_refresh_session,
            replaced_by_session_id=11,
        )
        self.assertEqual(result.access_token, "new-access-token")
        self.assertEqual(result.user.id, 1)

    async def test_get_me_returns_current_user_from_access_token(self) -> None:
        service = object.__new__(AuthBusinessService)
        user = build_user()
        service.token_service = MagicMock()
        service.token_service.decode_access_token.return_value = SimpleNamespace(
            sub="1"
        )
        service.user_service = MagicMock()
        service.user_service.get_user_by_id = AsyncMock(return_value=user)

        request = SimpleNamespace(
            headers={"authorization": "Bearer access-token"}
        )

        result = await AuthBusinessService.get_me(service, request)

        service.token_service.decode_access_token.assert_called_once_with(
            "access-token"
        )
        service.user_service.get_user_by_id.assert_awaited_once_with(1)
        self.assertEqual(result.id, 1)
        self.assertEqual(result.tg_id, 777)


class TokenServiceClaimsTests(TestCase):
    def setUp(self) -> None:
        self.service = TokenService(
            secret_key="unit-test-secret",
            algorithm="HS256",
            access_ttl_minutes=5,
            refresh_ttl_days=7,
        )
        self.user = build_user()

    def test_access_token_matches_claims_schema(self) -> None:
        token = self.service.create_access_token(self.user)
        payload = jwt.decode(token, "unit-test-secret", algorithms=["HS256"])

        try:
            claims = AccessTokenClaims.model_validate(payload)
        except ValidationError as exc:
            self.fail(f"Access token должен соответствовать AccessTokenClaims: {exc}")

        self.assertEqual(claims.token_type, "access")
        self.assertEqual(claims.sub, "1")
        self.assertEqual(claims.tg_id, 777)

    def test_refresh_token_matches_claims_schema(self) -> None:
        token = self.service.create_refresh_token(self.user)
        payload = jwt.decode(token, "unit-test-secret", algorithms=["HS256"])

        try:
            claims = RefreshTokenClaims.model_validate(payload)
        except ValidationError as exc:
            self.fail(f"Refresh token должен соответствовать RefreshTokenClaims: {exc}")

        self.assertEqual(claims.token_type, "refresh")
        self.assertEqual(claims.sub, "1")
        self.assertTrue(claims.jti)
