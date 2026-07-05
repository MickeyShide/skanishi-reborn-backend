from datetime import UTC, datetime

from app.db.models.event import Event
from app.db.repositories.event import EventRepository
from app.services.base import BaseService


class EventService(BaseService):
    repositories = {
        "event_repository": EventRepository,
    }

    event_repository: EventRepository

    async def get_active_event(self) -> Event | None:
        return await self.event_repository.get_active_event(datetime.now(UTC))
