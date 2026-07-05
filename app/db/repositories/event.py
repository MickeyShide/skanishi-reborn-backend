from datetime import datetime

from sqlalchemy import select

from app.db.models.event import Event
from app.db.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    model = Event

    async def get_active_event(self, now: datetime) -> Event | None:
        query = (
            select(Event)
            .where(
                Event.is_active.is_(True),
                Event.starts_at <= now,
                Event.ends_at > now,
            )
            .order_by(Event.ends_at.asc())
            .limit(1)
        )

        result = await self.session.execute(query)

        return result.scalar_one_or_none()
