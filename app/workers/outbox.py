import asyncio
import logging
from sqlalchemy import select
from app.core.celery_app import celery_app
from app.core.database import session_context
from app.db.models.system_events import OutboxEvent, OutboxEventStatus
from app.core.events import event_dispatcher

logger = logging.getLogger(__name__)

@celery_app.task
def publish_outbox_events():
    async def _run():
        async with session_context() as session:
            query = select(OutboxEvent).where(OutboxEvent.status == OutboxEventStatus.PENDING).limit(100)
            result = await session.execute(query)
            events = result.scalars().all()
            
            if not events:
                return

            for event in events:
                try:
                    event_dispatcher.emit(event.event_type, event.payload)
                    event.status = OutboxEventStatus.PUBLISHED
                except Exception as e:
                    logger.error(f"Failed to publish outbox event {event.id}: {e}")
            
            await session.commit()
            
    try:
        asyncio.run(_run())
    except Exception as e:
        logger.error(f"Error in publish_outbox_events task: {e}")
