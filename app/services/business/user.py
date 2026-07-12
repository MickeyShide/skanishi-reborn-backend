from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.schemas.user import (
    UserPrivacySettingsResponse,
    UserPrivacySettingsUpdateRequest,
)
from app.services.business.base import BusinessService
from app.services.user import UserService


class UserBusinessService(BusinessService):
    user_service: UserService

    def __init__(
        self,
        session: AsyncSession | None = None,
    ) -> None:
        super().__init__(session=session)

    async def get_privacy_settings(self, current_user: User) -> UserPrivacySettingsResponse:
        user = current_user

        return UserPrivacySettingsResponse(privacy=user.is_private)

    async def update_privacy_settings(
        self,
        current_user: User,
        dto: UserPrivacySettingsUpdateRequest,
    ) -> UserPrivacySettingsResponse:
        user = current_user
        updated_user = await self.user_service.update_privacy(
            user,
            is_private=dto.privacy,
        )

        self.user = updated_user

        return UserPrivacySettingsResponse(privacy=updated_user.is_private)
