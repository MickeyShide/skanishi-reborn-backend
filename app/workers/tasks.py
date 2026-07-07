import asyncio
import logging
from sqlalchemy import select
from app.core.celery_app import celery_app
from app.core.database import session_context
from app.services.user import UserService
from app.db.models.system_events import ProcessedEvent, OutboxEvent

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, queue="progress.commands")
def process_scan_claimed(self, payload: dict):
    from app.core.logger import request_id_ctx
    import uuid
    trace_id = payload.get("request_id") or str(uuid.uuid4())
    token = request_id_ctx.set(trace_id)
    
    event_id = payload["event_id"]
    user_id = payload["user_id"]
    reward_xp = payload["reward_xp"]
    scan_id = payload["scan_id"]
    
    async def _run():
        async with session_context() as session:
            # Idempotency check
            stmt = select(ProcessedEvent).where(ProcessedEvent.event_id == event_id)
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                logger.info(f"Event {event_id} already processed. Skipping.")
                return

            user_service = UserService(session)
            user = await user_service.get_user_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found during scan claim processing")
                return
            
            old_level = user.level
            
            # Add XP and check for level up
            logger.info(f"Processing level up for user {user_id} with +{reward_xp} XP")
            updated_user = await user_service.add_xp_and_check_level_up(user, reward_xp)
            
            new_level = updated_user.level
            
            # Real-time SSE notification via Redis Pub/Sub
            import json
            from app.core.redis_client import get_redis_client
            redis = await get_redis_client()
            await redis.publish(
                f"user_events:{user_id}",
                json.dumps({
                    "type": "xp_gained",
                    "xp": reward_xp,
                    "new_total": updated_user.xp,
                    "level": updated_user.level
                })
            )

            if new_level > old_level:
                logger.info(f"User {user_id} leveled up to {new_level}!")
                # Transactional outbox pattern for the new event
                outbox_event = OutboxEvent(
                    event_type="level_up",
                    payload={
                        "user_id": user.id,
                        "old_level": old_level,
                        "new_level": new_level,
                    }
                )
                session.add(outbox_event)
                
                await redis.publish(
                    f"user_events:{user_id}",
                    json.dumps({
                        "type": "level_up",
                        "old_level": old_level,
                        "new_level": new_level
                    })
                )
            
            # Mark event as processed
            processed_event = ProcessedEvent(event_id=event_id, status="DONE")
            session.add(processed_event)
            
            await session.commit()
            logger.info(f"User {user_id} is now level {updated_user.level} with {updated_user.xp} XP")
            
    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.error(f"Error processing scan claim for event {event_id}: {exc}")
        raise self.retry(exc=exc, countdown=5)
    finally:
        request_id_ctx.reset(token)

@celery_app.task(bind=True, max_retries=3, queue="notifications.commands")
def send_notification(self, payload: dict):
    from app.core.logger import request_id_ctx
    import uuid
    trace_id = payload.get("request_id") or str(uuid.uuid4())
    token = request_id_ctx.set(trace_id)
    try:
        # Stub for future notification sending
        logger.info(f"Sending notification: {payload}")
    finally:
        request_id_ctx.reset(token)

