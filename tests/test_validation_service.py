from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from app.services.validation import ValidationService


class ValidationServiceTests(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.session_mock = AsyncMock()
        self.service = ValidationService(session=self.session_mock)

        # Mock the repository
        self.service.validation_repository = AsyncMock()

    async def test_get_user_item_ids(self) -> None:
        self.service.validation_repository.get_user_item_ids.return_value = {1, 2}
        
        result = await self.service.get_user_item_ids(user_id=1, item_ids=[1, 2, 3])
        
        self.assertEqual(result, {1, 2})
        self.service.validation_repository.get_user_item_ids.assert_awaited_once_with(
            user_id=1, item_ids=[1, 2, 3]
        )

    async def test_get_user_item_secret_ids(self) -> None:
        self.service.validation_repository.get_user_item_secret_ids.return_value = {4}
        
        result = await self.service.get_user_item_secret_ids(user_id=1, item_secret_ids=[4, 5])
        
        self.assertEqual(result, {4})
        self.service.validation_repository.get_user_item_secret_ids.assert_awaited_once_with(
            user_id=1, item_secret_ids=[4, 5]
        )

    async def test_create_validation(self) -> None:
        mock_validation = AsyncMock()
        self.service.validation_repository.create.return_value = mock_validation

        result = await self.service.create_validation(
            user_id=1, item_id=2, item_secret_id=3, rank=5
        )

        self.assertEqual(result, mock_validation)
        self.service.validation_repository.create.assert_awaited_once_with(
            user_id=1, item_id=2, item_secret_id=3, rank=5
        )

    async def test_get_item_rating_page(self) -> None:
        self.service.validation_repository.get_item_rating_page.return_value = []

        result = await self.service.get_item_rating_page(item_id=2, limit=10, offset=0)

        self.assertEqual(result, [])
        self.service.validation_repository.get_item_rating_page.assert_awaited_once_with(
            item_id=2, limit=10, offset=0
        )
