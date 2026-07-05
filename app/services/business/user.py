from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.schemas.user import (
    UserPrivacySettingsResponse,
    UserPrivacySettingsUpdateRequest,
)
from app.services.business.base_authenticated import AuthenticatedBusinessService


class UserBusinessService(AuthenticatedBusinessService):
    def __init__(
        self,
        request: Request,
        session: AsyncSession | None = None,
    ) -> None:
        super().__init__(request=request, session=session)

    async def get_privacy_settings(self) -> UserPrivacySettingsResponse:
        user = await self.get_current_user()

        return UserPrivacySettingsResponse(privacy=user.is_private)

    async def update_privacy_settings(
        self,
        dto: UserPrivacySettingsUpdateRequest,
    ) -> UserPrivacySettingsResponse:
        user = await self.get_current_user()
        updated_user = await self.user_service.update_privacy(
            user,
            is_private=dto.privacy,
        )

        self.user = updated_user

        return UserPrivacySettingsResponse(privacy=updated_user.is_private)
