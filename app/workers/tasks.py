from __future__ import annotations

import asyncio
import json
import logging
import uuid

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import session_context
from app.core.redis_client import redis_client
from app.db.models.system_events import OutboxEvent, ProcessedEvent
from app.services.user import UserService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, queue="progress.commands")
def process_scan_claimed(self, payload: dict) -> None:
    """
    Process a scan_claimed outbox event.

    Responsibilities:
      1. Idempotency check via ProcessedEvent.
      2. Update user.xp and user.level (the canonical source of truth).
      3. Publish SSE notifications for xp_gained and level_up.

    Note on XP synchronisation:
      XpEvent (history log) is written synchronously in the HTTP handler
      inside the same transaction as the OutboxEvent.
      user.xp / user.level are updated here, after the commit, to avoid
      blocking the HTTP response.  The HTTP response returns the *expected*
      new XP (user.xp + reward_xp) computed optimistically on the frontend.
      If this worker fails and retries, the idempotency guard prevents
      double-increment of user.xp.
    """
    from app.core.logger import request_id_ctx  # local to avoid circular import at module load

    trace_id = payload.get("request_id") or str(uuid.uuid4())
    token = request_id_ctx.set(trace_id)

    event_id: str = payload["event_id"]
    user_id: int = payload["user_id"]
    reward_xp: int = payload.get("reward_xp", 0)
    reward_coins: int = payload.get("reward_coins", 0)
    reward_fragment_amount: int = payload.get("reward_fragment_amount", 0)
    reward_fragment_rarity: str = payload.get("reward_fragment_rarity", "")

    async def _run() -> None:
        async with session_context() as session:
            # 1. Idempotency: skip if already processed
            existing = (
                await session.execute(
                    select(ProcessedEvent).where(ProcessedEvent.event_id == event_id)
                )
            ).scalar_one_or_none()
            if existing:
                logger.info("Event %s already processed — skipping.", event_id)
                return

            # 2. Load user
            user_service = UserService(session)
            user = await user_service.get_user_by_id(user_id)
            if user is None:
                logger.warning(
                    "User %s not found while processing event %s — skipping.",
                    user_id,
                    event_id,
                )
                # Mark processed so we don't retry forever for a deleted user.
                session.add(ProcessedEvent(event_id=event_id, status="SKIPPED"))
                await session.commit()
                return

            old_level = user.level
            # 3. Apply XP and level-up logic
            logger.info(
                "Applying +%s XP to user %s (current xp=%s).",
                reward_xp,
                user_id,
                user.xp,
            )
            updated_user = await user_service.add_xp_and_check_level_up(user, reward_xp)
            if reward_coins > 0:
                logger.info("Adding +%s Coins to user %s.", reward_coins, user_id)
                updated_user.coins += reward_coins

            if reward_fragment_amount > 0 and reward_fragment_rarity:
                logger.info("Adding +%s %s Fragments to user %s.", reward_fragment_amount, reward_fragment_rarity, user_id)
                await user_service.add_fragment(
                    updated_user,
                    reward_fragment_rarity,
                    reward_fragment_amount,
                )

            new_level = updated_user.level

            # 4. Emit level_up outbox event if needed (before commit)
            if new_level > old_level:
                logger.info("User %s leveled up: %s → %s.", user_id, old_level, new_level)
                session.add(
                    OutboxEvent(
                        event_type="level_up",
                        payload={
                            "user_id": user_id,
                            "old_level": old_level,
                            "new_level": new_level,
                        },
                    )
                )

            # 5. Mark event as processed
            session.add(ProcessedEvent(event_id=event_id, status="DONE"))

            # 6. Single commit: user.xp + ProcessedEvent + optional OutboxEvent
            await session.commit()
            logger.info(
                "User %s → level=%s xp=%s.",
                user_id,
                updated_user.level,
                updated_user.xp,
            )

        # 7. Publish SSE notifications *after* commit (best-effort; Redis failure is non-fatal)
        try:
            channel = f"user_events:{user_id}"
            await redis_client.publish(
                channel,
                json.dumps(
                    {
                        "type": "xp_gained",
                        "xp": reward_xp,
                        "new_total": updated_user.xp,
                        "level": updated_user.level,
                    }
                ),
            )
            if new_level > old_level:
                await redis_client.publish(
                    channel,
                    json.dumps(
                        {
                            "type": "level_up",
                            "old_level": old_level,
                            "new_level": new_level,
                        }
                    ),
                )
        except Exception as redis_exc:  # noqa: BLE001
            logger.warning(
                "Redis publish failed for user %s (non-fatal): %s",
                user_id,
                redis_exc,
            )

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("Error processing scan_claimed event %s: %s", event_id, exc)
        raise self.retry(exc=exc, countdown=5) from exc
    finally:
        request_id_ctx.reset(token)


@celery_app.task(bind=True, max_retries=3, queue="progress.commands")
def process_ugc_passive_income(self, payload: dict) -> None:
    from app.core.logger import request_id_ctx
    from app.db.models.user_stickers import UserSticker

    trace_id = payload.get("request_id") or str(uuid.uuid4())
    token = request_id_ctx.set(trace_id)

    event_id: str = payload["event_id"]
    creator_id: int = payload["creator_id"]
    reward_xp: int = payload.get("reward_xp", 0)
    reward_coins: int = payload.get("reward_coins", 0)
    sticker_id: int = payload["sticker_id"]

    async def _run() -> None:
        async with session_context() as session:
            existing = (
                await session.execute(
                    select(ProcessedEvent).where(ProcessedEvent.event_id == event_id)
                )
            ).scalar_one_or_none()
            if existing:
                return

            user_service = UserService(session)
            creator = await user_service.get_user_by_id(creator_id)
            if not creator:
                session.add(ProcessedEvent(event_id=event_id, status="SKIPPED"))
                await session.commit()
                return

            old_level = creator.level
            updated_creator = await user_service.add_xp_and_check_level_up(creator, reward_xp)
            if reward_coins > 0:
                updated_creator.coins += reward_coins
            new_level = updated_creator.level

            sticker = await session.get(UserSticker, sticker_id)
            if sticker:
                sticker.total_passive_xp += reward_xp
                sticker.total_passive_coins += reward_coins

            if new_level > old_level:
                session.add(
                    OutboxEvent(
                        event_type="level_up",
                        payload={
                            "user_id": creator_id,
                            "old_level": old_level,
                            "new_level": new_level,
                        },
                    )
                )

            session.add(ProcessedEvent(event_id=event_id, status="DONE"))
            await session.commit()

        try:
            channel = f"user_events:{creator_id}"
            await redis_client.publish(
                channel,
                json.dumps(
                    {
                        "type": "ugc_income_received",
                        "xp": reward_xp,
                        "coins": reward_coins,
                        "new_total_xp": updated_creator.xp,
                        "new_total_coins": updated_creator.coins,
                    }
                ),
            )
        except Exception as redis_exc:
            logger.warning("Redis publish failed for user %s: %s", creator_id, redis_exc)

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("Error processing ugc_passive_income event %s: %s", event_id, exc)
        raise self.retry(exc=exc, countdown=5) from exc
    finally:
        request_id_ctx.reset(token)


@celery_app.task(bind=True, max_retries=3, queue="notifications.commands")
def send_notification(self, payload: dict) -> None:
    """
    Send a real-time SSE notification to a specific user.

    Expected payload:
      {
        "user_id": int,
        "type": str,          # SSE event type, e.g. "achievement_unlocked"
        "data": dict,         # arbitrary event data
        "request_id": str     # optional trace id
      }
    """
    from app.core.logger import request_id_ctx

    trace_id = payload.get("request_id") or str(uuid.uuid4())
    token = request_id_ctx.set(trace_id)

    user_id = payload.get("user_id")
    event_type = payload.get("type", "notification")
    data = payload.get("data", {})

    async def _run() -> None:
        if not user_id:
            logger.warning("send_notification called without user_id; payload=%s", payload)
            return

        channel = f"sse:user:{user_id}"
        message = json.dumps({"type": event_type, "data": data})
        try:
            await redis_client.publish(channel, message)
            logger.info("Notification '%s' sent to user %s.", event_type, user_id)
        except Exception as redis_exc:  # noqa: BLE001
            logger.warning(
                "Failed to send notification to user %s: %s",
                user_id,
                redis_exc,
            )
            raise
            
        # Send Push Notification via Telegram for important events
        important_events = {"level_up", "quest_completed", "achievement_unlocked", "collection_completed"}
        if event_type in important_events:
            from app.db.models.user import User
            from app.services.telegram import TelegramService
            
            async with session_context() as session:
                user = await session.get(User, user_id)
                if user and user.tg_id:
                    text_msg = f"🔔 <b>Событие:</b> {event_type}\n"
                    if event_type == "level_up":
                        text_msg += f"Поздравляем! Ваш новый уровень: {data.get('new_level')} 🚀"
                    elif event_type == "quest_completed":
                        text_msg += f"Квест завершен! Вы получили {data.get('reward_xp')} XP ✨"
                    elif event_type == "achievement_unlocked":
                        text_msg += f"Открыто достижение: {data.get('achievement_name')} 🏆"
                    elif event_type == "collection_completed":
                        text_msg += "Коллекция собрана! 🎉"
                        
                    telegram_service = TelegramService()
                    await telegram_service.send_message(user.tg_id, text_msg)

    try:
        return asyncio.Runner().run(_run())
    except Exception as exc:
        logger.error("Error in send_notification for user %s: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=5) from exc
    finally:
        request_id_ctx.reset(token)


@celery_app.task(queue="default")
def reset_expired_streaks() -> None:
    """
    Celery Beat task: runs every hour.
    Resets streak_days to 0 for users who have not logged in
    within the past 25 hours (grace period of 1 hour beyond a calendar day).
    """
    async def _run() -> None:
        from datetime import UTC, datetime, timedelta

        from sqlalchemy import update

        from app.db.models.user import User

        cutoff = datetime.now(UTC) - timedelta(hours=25)

        async with session_context() as session:
            result = await session.execute(
                update(User)
                .where(
                    User.streak_days > 0,
                    User.last_login_at.is_not(None),
                    User.last_login_at < cutoff,
                )
                .values(streak_days=0)
                .returning(User.id)
            )
            reset_ids = list(result.scalars().all())
            await session.commit()

        if reset_ids:
            logger.info("Reset streak for %d users: %s", len(reset_ids), reset_ids[:20])

    asyncio.run(_run())


@celery_app.task(queue="default")
def cleanup_processed_events() -> None:
    """
    Celery Beat task: runs every 24 hours.
    Deletes ProcessedEvent rows older than 30 days to keep the table lean.
    """
    async def _run() -> None:
        from datetime import UTC, datetime, timedelta

        from sqlalchemy import delete

        cutoff = datetime.now(UTC) - timedelta(days=30)

        async with session_context() as session:
            result = await session.execute(
                delete(ProcessedEvent).where(ProcessedEvent.created_at < cutoff)
            )
            await session.commit()
            logger.info(
                "Deleted %d old ProcessedEvent rows (older than %s).",
                result.rowcount,
                cutoff.date(),
            )

    asyncio.run(_run())


@celery_app.task(queue="default")
def cleanup_refresh_sessions() -> None:
    """
    Celery Beat task: runs every 24 hours.
    Deletes expired RefreshSession rows.
    """
    async def _run() -> None:
        from datetime import UTC, datetime

        from sqlalchemy import delete

        from app.db.models.refresh_session import RefreshSession

        now = datetime.now(UTC)

        async with session_context() as session:
            result = await session.execute(
                delete(RefreshSession).where(RefreshSession.expires_at < now)
            )
            await session.commit()
            logger.info(
                "Deleted %d expired RefreshSession rows.",
                result.rowcount,
            )

    asyncio.run(_run())


@celery_app.task(queue="default")
def update_rankings() -> None:
    """
    Celery Beat task: runs every 5 minutes.
    Updates the rank column on users based on XP descending.
    Only public users participate in the ranking.
    """
    async def _run() -> None:
        from sqlalchemy import text

        async with session_context() as session:
            await session.execute(
                text(
                    """
                    UPDATE users
                    SET rank = ranked.rn
                    FROM (
                        SELECT id,
                               RANK() OVER (ORDER BY xp DESC) AS rn
                        FROM users
                        WHERE is_private = FALSE
                    ) AS ranked
                    WHERE users.id = ranked.id
                      AND users.is_private = FALSE
                    """
                )
            )
            await session.commit()
            logger.debug("Rankings updated.")

    asyncio.run(_run())
