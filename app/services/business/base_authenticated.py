from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.db.models.user import User
from app.db.repositories.errors import ObjectNotFoundError
from app.schemas.auth import AccessTokenClaims
from app.services.business.auth import get_bearer_token
from app.services.business.base import BusinessService
from app.services.errors import InvalidAccessTokenError, UserNotFoundError
from app.services.token import TokenService
from app.services.user import UserService


class AuthenticatedBusinessService(BusinessService):
    """
    Базовый класс для бизнес-сценариев,
    которым нужен текущий авторизованный пользователь.
    """

    user_service: UserService

    def __init__(
        self,
        request: Request,
        session: AsyncSession | None = None,
    ) -> None:
        self.request = request
        self.user: User | None = None
        self.access_claims: AccessTokenClaims | None = None
        self.token_service = TokenService()
        self.get_access_claims()
        super().__init__(session)

    def get_access_claims(self) -> AccessTokenClaims:
        if self.access_claims is not None:
            return self.access_claims

        access_token = get_bearer_token(self.request)
        self.access_claims = self.token_service.decode_access_token(access_token)

        return self.access_claims

    async def get_current_user(self) -> User:
        if self.user is not None:
            return self.user

        claims = self.get_access_claims()

        try:
            user_id = int(claims.sub)
        except ValueError as exc:
            raise InvalidAccessTokenError from exc

        try:
            self.user = await self.user_service.get_user_by_id(user_id)
        except ObjectNotFoundError as exc:
            raise UserNotFoundError from exc

        return self.user
