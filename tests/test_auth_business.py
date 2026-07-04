from contextlib import asynccontextmanager
import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
from fastapi.testclient import TestClient
from pydantic import ValidationError
from redis.exceptions import RedisError
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
from app.services.business.base import BusinessService
from app.services.errors import (
    ExpiredInitDataError,
    ExpiredAccessTokenError,
    ExpiredRefreshTokenError,
    InitDataReplayError,
    InvalidAccessTokenError,
    InvalidRefreshTokenError,
    InvalidTelegramSignatureError,
    MissingRefreshTokenError,
    RefreshReuseDetectedError,
    RevokedRefreshTokenError,
)
from app.services.init_data import TelegramInitDataService, TelegramUserData
from app.services.init_data_replay_guard import InitDataReplayGuardService
from app.services.refresh_session import RefreshSessionService
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
        self.assertIn("Path=/auth/refresh", response.headers["set-cookie"])

    async def test_authenticate_sets_csrf_cookie_when_samesite_none(self) -> None:
        service = object.__new__(AuthBusinessService)
        telegram_user = TelegramUserData(tg_id=777, first_name="Mickey")
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

        with patch.object(settings, "COOKIE_SAMESITE", "none"):
            await AuthBusinessService.authenticate(
                service,
                dto=dto,
                request=request,
                response=response,
            )

        set_cookie_headers = [
            value.decode()
            for name, value in response.raw_headers
            if name == b"set-cookie"
        ]
        self.assertTrue(
            any("refresh_token=refresh-token" in header for header in set_cookie_headers)
        )
        self.assertTrue(any("csrf_token=" in header for header in set_cookie_headers))


class AuthEndpointContractTests(TestCase):
    def test_auth_init_route_is_registered_in_application(self) -> None:
        response = TestClient(app, raise_server_exceptions=False).post("/auth/init")

        self.assertEqual(
            response.status_code,
            422,
            "Если endpoint подключен, запрос без обязательного body должен "
            "валидироваться как 422, а не пропадать с 404.",
        )

    def test_auth_init_handler_does_not_expose_session_dependency(self) -> None:
        import inspect

        parameters = inspect.signature(auth_api.auth_init).parameters

        self.assertNotIn(
            "session",
            parameters,
            "HTTP-хендлер не должен вручную принимать AsyncSession: "
            "бизнес-сервис сам владеет DB-сессией для сценария.",
        )
        self.assertNotIn(
            "auth_service",
            parameters,
            "HTTP-хендлер не должен требовать DI-зависимость бизнес-сервиса: "
            "AuthBusinessService создаётся внутри хендлера и сам владеет сессией.",
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
    def test_auth_business_service_can_be_constructed_without_session(self) -> None:
        try:
            service = AuthBusinessService()
        except TypeError as exc:
            self.fail(
                "Конструктор AuthBusinessService не должен требовать AsyncSession: "
                f"{exc}"
            )

        self.assertIsNone(service.session)
        self.assertTrue(hasattr(service, "telegram_init_data_service"))
        self.assertTrue(hasattr(service, "token_service"))

    def test_auth_business_service_still_accepts_existing_session(self) -> None:
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


class BusinessServiceLazySessionTests(IsolatedAsyncioTestCase):
    async def test_opens_session_on_child_service_use_and_closes_after_scenario(
        self,
    ) -> None:
        session = object()
        events: list[str] = []

        class ChildService:
            def __init__(self, session) -> None:
                self.session = session

            async def get_session(self):
                return self.session

        class LazyBusinessService(BusinessService):
            services = {"child_service": ChildService}

            async def run(self):
                return await self.child_service.get_session()

        @asynccontextmanager
        async def fake_session_context():
            events.append("open")
            try:
                yield session
            finally:
                events.append("close")

        with patch("app.services.business.base.session_context", fake_session_context):
            service = LazyBusinessService()
            result = await service.run()

        self.assertIs(result, session)
        self.assertIsNone(service.session)
        self.assertEqual(events, ["open", "close"])

    async def test_refresh_without_cookie_does_not_open_session(self) -> None:
        service = AuthBusinessService()
        request = SimpleNamespace(cookies={}, headers={})

        with patch("app.services.business.base.session_context") as session_context:
            with self.assertRaises(MissingRefreshTokenError):
                await service.refresh(request=request, response=Response())

        session_context.assert_not_called()


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

    async def test_refresh_sets_csrf_cookie_when_samesite_none(self) -> None:
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

        with patch.object(settings, "COOKIE_SAMESITE", "none"):
            await AuthBusinessService.refresh(
                service,
                request=request,
                response=response,
            )

        set_cookie_headers = [
            value.decode()
            for name, value in response.raw_headers
            if name == b"set-cookie"
        ]
        self.assertTrue(
            any(
                "refresh_token=new-refresh-token" in header
                for header in set_cookie_headers
            )
        )
        self.assertTrue(any("csrf_token=" in header for header in set_cookie_headers))

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

    def test_expired_access_token_raises_explicit_error(self) -> None:
        now = int(time.time())
        token = jwt.encode(
            {
                "sub": "1",
                "tg_id": 777,
                "role": "USER",
                "token_type": "access",
                "iat": now - 120,
                "exp": now - 60,
            },
            "unit-test-secret",
            algorithm="HS256",
        )

        with self.assertRaises(ExpiredAccessTokenError):
            self.service.decode_access_token(token)

    def test_invalid_access_token_type_raises_invalid_access_token(self) -> None:
        now = int(time.time())
        token = jwt.encode(
            {
                "sub": "1",
                "jti": "not-used-here",
                "token_type": "refresh",
                "iat": now,
                "exp": now + 300,
            },
            "unit-test-secret",
            algorithm="HS256",
        )

        with self.assertRaises(InvalidAccessTokenError):
            self.service.decode_access_token(token)

    def test_expired_refresh_token_raises_explicit_error(self) -> None:
        now = int(time.time())
        token = jwt.encode(
            {
                "sub": "1",
                "jti": "50e6c6d0-1e95-4202-856b-8450442143d2",
                "token_type": "refresh",
                "iat": now - 120,
                "exp": now - 60,
            },
            "unit-test-secret",
            algorithm="HS256",
        )

        with self.assertRaises(ExpiredRefreshTokenError):
            self.service.decode_refresh_token(token)

    def test_invalid_refresh_token_type_raises_invalid_refresh_token(self) -> None:
        now = int(time.time())
        token = jwt.encode(
            {
                "sub": "1",
                "tg_id": 777,
                "role": "USER",
                "token_type": "access",
                "iat": now,
                "exp": now + 300,
            },
            "unit-test-secret",
            algorithm="HS256",
        )

        with self.assertRaises(InvalidRefreshTokenError):
            self.service.decode_refresh_token(token)


class TelegramInitDataServiceTests(TestCase):
    def setUp(self) -> None:
        self.bot_token = "123456:unit-test-token"
        self.service = TelegramInitDataService(bot_token=self.bot_token)

    def build_init_data(
        self,
        *,
        auth_date: int | None = None,
        user_payload: dict[str, object] | None = None,
    ) -> str:
        payload = {
            "auth_date": str(auth_date if auth_date is not None else int(time.time())),
            "query_id": "AAEAAAE",
            "user": json.dumps(
                user_payload
                or {
                    "id": 777,
                    "first_name": "Mickey",
                    "username": "mickey",
                },
                separators=(",", ":"),
            ),
        }
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
        secret_key = hmac.new(
            b"WebAppData",
            self.bot_token.encode(),
            hashlib.sha256,
        ).digest()
        payload["hash"] = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        return "&".join(f"{key}={value}" for key, value in payload.items())

    def test_invalid_signature_raises_explicit_error(self) -> None:
        init_data = self.build_init_data() + "tampered"

        with self.assertRaises(InvalidTelegramSignatureError):
            self.service.validate_and_parse(init_data)

    def test_expired_init_data_raises_explicit_error(self) -> None:
        init_data = self.build_init_data(auth_date=int(time.time()) - 7200)

        with self.assertRaises(ExpiredInitDataError):
            self.service.validate_and_parse(init_data)


class InitDataReplayGuardServiceTests(IsolatedAsyncioTestCase):
    async def test_redis_failure_is_fail_open(self) -> None:
        redis = MagicMock()
        redis.set = AsyncMock(side_effect=RedisError("redis unavailable"))
        service = InitDataReplayGuardService(redis)

        await service.ensure_not_replayed("signed-init-data")

    async def test_replayed_init_data_is_rejected(self) -> None:
        redis = MagicMock()
        redis.set = AsyncMock(return_value=False)
        service = InitDataReplayGuardService(redis)

        with self.assertRaises(InitDataReplayError):
            await service.ensure_not_replayed("signed-init-data")


class RefreshSessionServiceTests(IsolatedAsyncioTestCase):
    async def test_refresh_reuse_is_detected(self) -> None:
        service = RefreshSessionService(session=object())
        service.token_service = MagicMock()
        service.token_service.decode_refresh_token.return_value = SimpleNamespace(
            jti="50e6c6d0-1e95-4202-856b-8450442143d2",
            exp=int(time.time()) + 3600,
        )
        service.refresh_session_repository = MagicMock()
        service.refresh_session_repository.get_by_jti_and_token_hash = AsyncMock(
            return_value=SimpleNamespace(
                revoked_at=SimpleNamespace(),
                replaced_by_session_id=11,
                expires_at=SimpleNamespace(),
            )
        )

        with self.assertRaises(RefreshReuseDetectedError):
            await service.get_session_for_refresh("reused-refresh-token")

    async def test_revoked_refresh_token_is_reported(self) -> None:
        service = RefreshSessionService(session=object())
        service.token_service = MagicMock()
        service.token_service.decode_refresh_token.return_value = SimpleNamespace(
            jti="50e6c6d0-1e95-4202-856b-8450442143d2",
            exp=int(time.time()) + 3600,
        )
        service.refresh_session_repository = MagicMock()
        service.refresh_session_repository.get_by_jti_and_token_hash = AsyncMock(
            return_value=SimpleNamespace(
                revoked_at=SimpleNamespace(),
                replaced_by_session_id=None,
                expires_at=SimpleNamespace(),
            )
        )

        with self.assertRaises(RevokedRefreshTokenError):
            await service.get_session_for_refresh("revoked-refresh-token")
