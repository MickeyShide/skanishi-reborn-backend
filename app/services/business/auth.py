# app/business/auth.py

from __future__ import annotations

from dataclasses import dataclass
import inspect
import secrets

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.core.redis_client import redis_client
from app.db.repositories.errors import ObjectNotFoundError
from app.schemas.auth import TelegramAuthRequest, TokenResponse
from app.schemas.user import UserMe
from app.services.business.base import BusinessService
from app.services.errors import (
    InvalidAccessTokenError,
    InvalidRefreshTokenError,
    MissingAuthorizationError,
    MissingRefreshTokenError,
    UserNotFoundError,
)
from app.services.init_data import TelegramInitDataService
from app.services.init_data_replay_guard import InitDataReplayGuardService
from app.services.refresh_session import RefreshSessionService
from app.services.token import TokenService
from app.services.user import UserService


@dataclass(slots=True)
class AuthTokenResult:
    response: TokenResponse
    refresh_token: str


REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth/refresh"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_COOKIE_PATH = "/"
CSRF_HEADER_NAME = "X-CSRF-Token"


def csrf_protection_enabled() -> bool:
    return settings.COOKIE_SAMESITE == "none"


def get_bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization")

    if not authorization:
        raise MissingAuthorizationError()

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise InvalidAccessTokenError()

    return token.strip()


def get_refresh_token(request: Request) -> str:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise MissingRefreshTokenError()

    return refresh_token


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_TTL_SECONDS,
        path=REFRESH_COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )


def set_csrf_cookie(response: Response) -> None:
    if not csrf_protection_enabled():
        return

    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=secrets.token_urlsafe(32),
        path=CSRF_COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE,
        httponly=False,
        samesite=settings.COOKIE_SAMESITE,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )


def clear_csrf_cookie(response: Response) -> None:
    if not csrf_protection_enabled():
        return

    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path=CSRF_COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE,
        httponly=False,
        samesite=settings.COOKIE_SAMESITE,
    )


class AuthBusinessService(BusinessService):
    telegram_init_data_service: TelegramInitDataService
    init_data_replay_guard_service: InitDataReplayGuardService
    user_service: UserService
    token_service: TokenService
    refresh_session_service: RefreshSessionService

    def __init__(self, session: AsyncSession | None = None) -> None:
        super().__init__(session)
        self.token_service = TokenService()
        self.telegram_init_data_service = TelegramInitDataService(
            bot_token=settings.BOT_TOKEN,
        )
        self.init_data_replay_guard_service = InitDataReplayGuardService(
            redis_client,
        )

    async def authenticate(
        self, dto: TelegramAuthRequest, request: Request, response: Response
    ) -> TokenResponse:
        """
        Business scenario: Telegram WebApp auth init.

        Возвращает:
            AuthTokenResult, где refresh-token нужен только API-слою для cookie.
        """

        # 1. Проверяем подпись, lifetime и парсим Telegram user.
        telegram_init_data = self.telegram_init_data_service.validate_and_parse(
            dto.tg_web_app_data,
        )

        # 2. Опциональная replay-защита.
        # Если для продукта это не критично, можно убрать этот шаг.
        await self.init_data_replay_guard_service.ensure_not_replayed(
            dto.tg_web_app_data,
        )

        # 3. Parse referral ID if present
        referred_by_id = None
        start_param = getattr(telegram_init_data, "start_param", None)
        if start_param and start_param.startswith("ref_"):
            try:
                referred_by_id = int(start_param.split("_")[1])
            except (ValueError, IndexError):
                pass

        # 4. Найти или создать пользователя.
        user_service_dict = getattr(self.user_service, "__dict__", {})
        if "get_or_create_from_telegram_with_status" in user_service_dict:
            if referred_by_id is None:
                user, is_new = await self.user_service.get_or_create_from_telegram_with_status(
                    telegram_init_data.user,
                )
            else:
                user, is_new = await self.user_service.get_or_create_from_telegram_with_status(
                    telegram_init_data.user,
                    referred_by_id=referred_by_id,
                )
        else:
            if referred_by_id is None:
                legacy_result = self.user_service.get_or_create_from_telegram(
                    telegram_init_data.user,
                )
            else:
                legacy_result = self.user_service.get_or_create_from_telegram(
                    telegram_init_data.user,
                    referred_by_id=referred_by_id,
                )
            user = await legacy_result if inspect.isawaitable(legacy_result) else legacy_result
            is_new = False

        # 4.1. Если пользователь новый и был приглашен, выдаем награды
        if is_new and user.referred_by_id:
            from app.db.models.xp_event import XpEvent
            # Награда приглашенному
            user = await self.user_service.add_xp_and_check_level_up(user, 500)
            self._session.add(XpEvent(user_id=user.id, source="referral_signup", xp_reward=500))
            
            # Награда пригласившему (получим и обновим)
            referrer = await self.user_service.get_user_by_id(user.referred_by_id)
            if referrer:
                referrer = await self.user_service.add_xp_and_check_level_up(referrer, 1000)
                self._session.add(XpEvent(user_id=referrer.id, source="referral_bonus", xp_reward=1000))
                # Optional: Send SSE/Push to referrer via Outbox (not strictly required here for MVP)
                from app.db.models.system_events import OutboxEvent
                self._session.add(OutboxEvent(
                    event_type="notification",
                    payload={
                        "user_id": referrer.id,
                        "type": "referral_success",
                        "data": {"bonus_xp": 1000, "friend_name": user.first_name}
                    }
                ))

        # 5. Создать токены.
        access_token = self.token_service.create_access_token(user)
        refresh_token = self.token_service.create_refresh_token(user)

        # 6. Сохранить refresh-сессию.
        await self.refresh_session_service.create_refresh_session(
            user_id=user.id,
            refresh_token=refresh_token,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )

        set_refresh_cookie(response, refresh_token)
        set_csrf_cookie(response)

        # 7. Наружу отдаём только access_token, refresh остается для cookie.
        return TokenResponse(
            access_token=access_token,
            expires_in=settings.ACCESS_TOKEN_TTL_SECONDS,
            user=UserMe.model_validate(user),
        )

    async def refresh(self, request: Request, response: Response) -> TokenResponse:
        refresh_token = get_refresh_token(request)
        claims = self.token_service.decode_refresh_token(refresh_token)

        try:
            user_id = int(claims.sub)
        except ValueError as exc:
            raise InvalidRefreshTokenError from exc

        refresh_session = (
            await self.refresh_session_service.get_session_for_refresh(
                refresh_token,
            )
        )

        if refresh_session.user_id != user_id:
            raise InvalidRefreshTokenError()

        try:
            user = await self.user_service.get_user_by_id(user_id)
        except ObjectNotFoundError as exc:
            raise InvalidRefreshTokenError from exc

        access_token = self.token_service.create_access_token(user)
        new_refresh_token = self.token_service.create_refresh_token(user)
        new_refresh_session = (
            await self.refresh_session_service.create_refresh_session(
                user_id=user.id,
                refresh_token=new_refresh_token,
                user_agent=request.headers.get("user-agent"),
                ip_address=request.client.host if request.client else None,
            )
        )
        await self.refresh_session_service.revoke_refresh_session(
            refresh_session,
            replaced_by_session_id=new_refresh_session.id,
        )

        set_refresh_cookie(response, new_refresh_token)
        set_csrf_cookie(response)

        return TokenResponse(
            access_token=access_token,
            expires_in=settings.ACCESS_TOKEN_TTL_SECONDS,
            user=UserMe.model_validate(user),
        )

    async def logout(self, request: Request, response: Response) -> None:
        refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
        if not refresh_token:
            return

        clear_refresh_cookie(response)
        clear_csrf_cookie(response)

        await self.refresh_session_service.revoke_by_refresh_token(refresh_token)

    async def get_me(self, request: Request) -> UserMe:
        access_token = get_bearer_token(request)
        claims = self.token_service.decode_access_token(access_token)

        try:
            user_id = int(claims.sub)
        except ValueError as exc:
            raise InvalidAccessTokenError from exc

        try:
            user = await self.user_service.get_user_by_id(user_id)
        except ObjectNotFoundError as exc:
            raise UserNotFoundError from exc

        return UserMe.model_validate(user)
