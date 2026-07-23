from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.repositories.user import UserRepository


class UserRepositoryTests(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.session_mock = AsyncMock(spec=AsyncSession)
        self.repo = UserRepository(session=self.session_mock)

    async def test_get_by_tg_id(self) -> None:
        mock_result = MagicMock()
        mock_user = User(tg_id=123)
        mock_result.scalar_one_or_none.return_value = mock_user
        self.session_mock.execute.return_value = mock_result

        result = await self.repo.get_by_tg_id(123)

        self.assertEqual(result, mock_user)
        self.session_mock.execute.assert_awaited_once()
