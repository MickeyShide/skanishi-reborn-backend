from datetime import datetime
from decimal import Decimal

from app.db.models.enums import UIColorToken
from app.db.models.xp_event import XpEvent
from app.db.repositories.xp_event import XpEventRepository
from app.services.base import BaseService


class XpEventService(BaseService):
    repositories = {
        "xp_event_repository": XpEventRepository,
    }

    xp_event_repository: XpEventRepository

    async def get_user_history(
        self,
        *,
        user_id: int,
        limit: int,
        offset: int,
        tag: str | None = None,
    ) -> list[XpEvent]:
        return await self.xp_event_repository.get_user_history(
            user_id=user_id,
            limit=limit,
            offset=offset,
            tag=tag,
        )

    async def get_recent_user_events(
        self,
        *,
        user_id: int,
        limit: int,
    ) -> list[XpEvent]:
        return await self.xp_event_repository.get_recent_user_events(
            user_id=user_id,
            limit=limit,
        )

    async def get_user_event_by_source(
        self,
        *,
        user_id: int,
        source: str,
    ) -> XpEvent | None:
        return await self.xp_event_repository.get_user_event_by_source(
            user_id=user_id,
            source=source,
        )

    async def get_user_claimed_scan_sources(
        self,
        *,
        user_id: int,
        sources: list[str],
    ) -> set[str]:
        return await self.xp_event_repository.get_user_claimed_scan_sources(
            user_id=user_id,
            sources=sources,
        )

    async def count_user_events_by_tag(
        self,
        *,
        user_id: int,
        tag: str,
    ) -> int:
        return await self.xp_event_repository.count_user_events_by_tag(
            user_id=user_id,
            tag=tag,
        )

    async def get_user_events_between(
        self,
        *,
        user_id: int,
        occurred_at_from: datetime,
        occurred_at_to: datetime,
        tag: str | None = None,
    ) -> list[XpEvent]:
        return await self.xp_event_repository.get_user_events_between(
            user_id=user_id,
            occurred_at_from=occurred_at_from,
            occurred_at_to=occurred_at_to,
            tag=tag,
        )

    async def sum_user_xp_since(
        self,
        *,
        user_id: int,
        occurred_at_from: datetime,
    ) -> int:
        return await self.xp_event_repository.sum_user_xp_since(
            user_id=user_id,
            occurred_at_from=occurred_at_from,
        )

    async def create_scan_claim_event(
        self,
        *,
        user_id: int,
        scan_id: str,
        reward_xp: int,
        occurred_at: datetime,
        color: UIColorToken = UIColorToken.CYAN,
    ) -> XpEvent:
        return await self.xp_event_repository.create(
            user_id=user_id,
            source=self.build_scan_source(scan_id),
            tag="SCAN",
            xp=reward_xp,
            multiplier=Decimal("1.00"),
            color=color,
            occurred_at=occurred_at,
        )

    @staticmethod
    def build_scan_source(scan_id: str) -> str:
        return f"scan:{scan_id}"
