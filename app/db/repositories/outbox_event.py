from app.db.models.system_events import OutboxEvent
from app.db.repositories.base import BaseRepository


class OutboxEventRepository(BaseRepository[OutboxEvent]):
    model = OutboxEvent
