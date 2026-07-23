from typing import Any

from app.db.models.system_events import OutboxEvent
from app.db.repositories.outbox_event import OutboxEventRepository
from app.services.base import BaseService


class OutboxService(BaseService):
    repositories = {"outbox_event_repository": OutboxEventRepository}

    outbox_event_repository: OutboxEventRepository

    async def create_event(self, *, event_type: str, payload: dict[str, Any]) -> OutboxEvent:
        return await self.outbox_event_repository.create(
            event_type=event_type,
            payload=payload,
        )
