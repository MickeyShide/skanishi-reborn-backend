from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from app.db.repositories.base import BaseRepository

Base = declarative_base()

from sqlalchemy import Column, Integer, String

class DummyModel(Base):
    __tablename__ = "dummy"
    id = Column(Integer, primary_key=True)
    name = Column(String)


class DummyRepository(BaseRepository[DummyModel]):
    model = DummyModel


class BaseRepositoryTests(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.session_mock = AsyncMock(spec=AsyncSession)
        self.repo = DummyRepository(session=self.session_mock)

    async def test_get(self) -> None:
        mock_result = MagicMock()
        mock_model = DummyModel()
        mock_result.scalar_one_or_none.return_value = mock_model
        self.session_mock.execute.return_value = mock_result

        result = await self.repo.get(1)

        self.assertEqual(result, mock_model)
        self.session_mock.execute.assert_awaited_once()

    async def test_create(self) -> None:
        result = await self.repo.create(name="test")

        self.assertIsInstance(result, DummyModel)
        self.session_mock.add.assert_called_once_with(result)
        self.session_mock.flush.assert_awaited_once()
        self.session_mock.refresh.assert_awaited_once_with(result)

    async def test_update(self) -> None:
        mock_model = DummyModel()
        
        result = await self.repo.update(mock_model, name="updated")

        self.assertEqual(result, mock_model)
        self.session_mock.add.assert_called_once_with(mock_model)
        self.session_mock.flush.assert_awaited_once()
        self.session_mock.refresh.assert_awaited_once_with(mock_model)

    async def test_delete(self) -> None:
        mock_model = DummyModel()
        
        await self.repo.delete(mock_model)

        self.session_mock.delete.assert_awaited_once_with(mock_model)
        self.session_mock.flush.assert_awaited_once()
