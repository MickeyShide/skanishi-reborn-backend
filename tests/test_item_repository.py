from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.item import ItemRepository


class ItemRepositoryTests(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.session_mock = AsyncMock(spec=AsyncSession)
        self.repo = ItemRepository(session=self.session_mock)

    async def test_get_active_catalog_page(self) -> None:
        mock_result = MagicMock()
        mock_result.all.return_value = [("Item1", "Cat1", "Proto1", "Type1")]
        self.session_mock.execute.return_value = mock_result

        result = await self.repo.get_active_catalog_page(limit=10, offset=0, category_id=1)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], ("Item1", "Cat1", "Proto1", "Type1"))
        self.session_mock.execute.assert_awaited_once()

    async def test_count_active_catalog(self) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        self.session_mock.execute.return_value = mock_result

        result = await self.repo.count_active_catalog()

        self.assertEqual(result, 5)
        self.session_mock.execute.assert_awaited_once()

    async def test_get_active_catalog_item(self) -> None:
        mock_result = MagicMock()
        mock_result.first.return_value = ("Item1", "Cat1", "Proto1", "Type1")
        self.session_mock.execute.return_value = mock_result

        result = await self.repo.get_active_catalog_item(item_id=1)

        self.assertEqual(result, ("Item1", "Cat1", "Proto1", "Type1"))
        self.session_mock.execute.assert_awaited_once()

    async def test_get_active_item_by_id(self) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "ItemModel"
        self.session_mock.execute.return_value = mock_result

        result = await self.repo.get_active_item_by_id(item_id=1)

        self.assertEqual(result, "ItemModel")
        self.session_mock.execute.assert_awaited_once()

    async def test_get_active_item_for_update(self) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "LockedItemModel"
        self.session_mock.execute.return_value = mock_result

        result = await self.repo.get_active_item_for_update(item_id=1)

        self.assertEqual(result, "LockedItemModel")
        self.session_mock.execute.assert_awaited_once()
