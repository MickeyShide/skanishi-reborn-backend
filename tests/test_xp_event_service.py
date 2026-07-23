from datetime import datetime, timezone
from decimal import Decimal
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from app.db.models.enums import UIColorToken
from app.services.xp_event import XpEventService


class XpEventServiceTests(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.session_mock = AsyncMock()
        self.service = XpEventService(session=self.session_mock)
        self.service.xp_event_repository = AsyncMock()

    async def test_get_user_history(self) -> None:
        self.service.xp_event_repository.get_user_history.return_value = []
        
        result = await self.service.get_user_history(user_id=1, limit=10, offset=0, tag="QUEST")
        
        self.assertEqual(result, [])
        self.service.xp_event_repository.get_user_history.assert_awaited_once_with(
            user_id=1, limit=10, offset=0, tag="QUEST"
        )

    async def test_get_recent_user_events(self) -> None:
        self.service.xp_event_repository.get_recent_user_events.return_value = []
        
        result = await self.service.get_recent_user_events(user_id=1, limit=5)
        
        self.assertEqual(result, [])
        self.service.xp_event_repository.get_recent_user_events.assert_awaited_once_with(
            user_id=1, limit=5
        )

    async def test_get_user_event_by_source(self) -> None:
        mock_event = AsyncMock()
        self.service.xp_event_repository.get_user_event_by_source.return_value = mock_event
        
        result = await self.service.get_user_event_by_source(user_id=1, source="scan:123")
        
        self.assertEqual(result, mock_event)
        self.service.xp_event_repository.get_user_event_by_source.assert_awaited_once_with(
            user_id=1, source="scan:123"
        )

    async def test_create_scan_claim_event(self) -> None:
        mock_event = AsyncMock()
        self.service.xp_event_repository.create.return_value = mock_event
        now = datetime.now(timezone.utc)
        
        result = await self.service.create_scan_claim_event(
            user_id=1,
            scan_id="abc",
            reward_xp=100,
            occurred_at=now,
            color=UIColorToken.RED
        )
        
        self.assertEqual(result, mock_event)
        self.service.xp_event_repository.create.assert_awaited_once_with(
            user_id=1,
            source="scan:abc",
            tag="SCAN",
            xp=100,
            multiplier=Decimal("1.00"),
            color=UIColorToken.RED,
            occurred_at=now
        )
