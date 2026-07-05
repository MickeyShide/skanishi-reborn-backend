from datetime import datetime

from sqlalchemy import func, select

from app.db.models.xp_event import XpEvent
from app.db.repositories.base import BaseRepository


class XpEventRepository(BaseRepository[XpEvent]):
    model = XpEvent

    async def get_user_history(
        self,
        *,
        user_id: int,
        limit: int,
        offset: int,
        tag: str | None = None,
    ) -> list[XpEvent]:
        query = select(XpEvent).where(XpEvent.user_id == user_id)

        if tag is not None:
            query = query.where(XpEvent.tag == tag)

        query = query.order_by(XpEvent.occurred_at.desc(), XpEvent.id.desc())
        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)

        return list(result.scalars().all())

    async def get_recent_user_events(
        self,
        *,
        user_id: int,
        limit: int,
    ) -> list[XpEvent]:
        query = (
            select(XpEvent)
            .where(XpEvent.user_id == user_id)
            .order_by(XpEvent.occurred_at.desc(), XpEvent.id.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)

        return list(result.scalars().all())

    async def get_user_event_by_source(
        self,
        *,
        user_id: int,
        source: str,
    ) -> XpEvent | None:
        query = (
            select(XpEvent)
            .where(
                XpEvent.user_id == user_id,
                XpEvent.source == source,
            )
            .limit(1)
        )

        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    async def get_user_claimed_scan_sources(
        self,
        *,
        user_id: int,
        sources: list[str],
    ) -> set[str]:
        if not sources:
            return set()

        query = select(XpEvent.source).where(
            XpEvent.user_id == user_id,
            XpEvent.source.in_(sources),
        )

        result = await self.session.execute(query)

        return set(result.scalars().all())

    async def count_user_events_by_tag(
        self,
        *,
        user_id: int,
        tag: str,
    ) -> int:
        query = select(func.count()).select_from(XpEvent).where(
            XpEvent.user_id == user_id,
            XpEvent.tag == tag,
        )

        result = await self.session.execute(query)

        return int(result.scalar_one())

    async def sum_user_xp_since(
        self,
        *,
        user_id: int,
        occurred_at_from: datetime,
    ) -> int:
        query = select(func.coalesce(func.sum(XpEvent.xp), 0)).where(
            XpEvent.user_id == user_id,
            XpEvent.occurred_at >= occurred_at_from,
        )

        result = await self.session.execute(query)

        return int(result.scalar_one())
