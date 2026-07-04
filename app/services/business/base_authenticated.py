# app/business/authenticated.py

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.repositories.errors import ObjectNotFoundError
from app.services.business.base import BusinessService
from app.services.errors import UnauthorizedError, UserNotFoundError
from app.services.user import UserService


class AuthenticatedBusinessService(BusinessService):
    """
    Базовый класс для бизнес-сценариев,
    которым нужен текущий авторизованный пользователь.
    """

    user_service: UserService

    def __init__(
        self,
        token_data: dict[str, Any] | None,
        session: AsyncSession | None = None,
    ) -> None:
        super().__init__(session)
        self.token_data = token_data
        self.user: User | None = None

    async def get_current_user(self) -> User:
        if self.user is not None:
            return self.user

        if not self.token_data or "id" not in self.token_data:
            raise UnauthorizedError

        try:
            self.user = await self.user_service.get_user_by_id(
                int(self.token_data["id"])
            )
        except ObjectNotFoundError as exc:
            raise UserNotFoundError from exc

        return self.user
