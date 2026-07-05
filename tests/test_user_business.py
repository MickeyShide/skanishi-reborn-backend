from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from app.schemas.user import UserPrivacySettingsUpdateRequest
from app.services.business.user import UserBusinessService


class UserBusinessServiceTests(IsolatedAsyncioTestCase):
    async def test_get_privacy_settings_returns_current_value(self) -> None:
        user = SimpleNamespace(id=77, is_private=True)
        service = object.__new__(UserBusinessService)
        result = await UserBusinessService.get_privacy_settings(service, user)

        self.assertTrue(result.privacy)

    async def test_update_privacy_settings_updates_user_and_returns_new_value(
        self,
    ) -> None:
        user = SimpleNamespace(id=77, is_private=True)
        updated_user = SimpleNamespace(id=77, is_private=False)
        service = object.__new__(UserBusinessService)
        service.user_service = MagicMock()
        service.user_service.update_privacy = AsyncMock(return_value=updated_user)
        service.user = user

        result = await UserBusinessService.update_privacy_settings(
            service,
            user,
            UserPrivacySettingsUpdateRequest(privacy=False),
        )

        service.user_service.update_privacy.assert_awaited_once_with(
            user,
            is_private=False,
        )
        self.assertFalse(result.privacy)
        self.assertEqual(service.user.id, updated_user.id)
