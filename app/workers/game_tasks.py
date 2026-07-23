"""Side-effect Celery workers triggered by scan_claimed outbox events.

These workers react to a scan and check/update:
  - Quest progress (per-user)
  - Achievement unlock conditions
  - Collection completion

All workers are fully idempotent.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.core.celery_app import celery_app
from app.core.database import session_context
from app.core.events import event_dispatcher
from app.db.models.user_quest import UserQuest

logger = logging.getLogger(__name__)
UserQuestModel = UserQuest


# ──────────────────────────────────────────────────────────────────────────────
# Quest Progress Worker
# ──────────────────────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, queue="progress.commands")
def process_quest_progress(
    self,
    payload: dict,
) -> None:
    """Increment UserQuest.progress for all applicable active quests.

    A quest is applicable if:
      - It is active
      - Its condition_tag is None (applies to all scans) OR matches the
        tag attached to this scan's XpEvent
      - The user has not yet completed it (completed_at IS NULL)
    """
    from app.core.logger import request_id_ctx

    trace_id = payload.get("request_id") or str(uuid.uuid4())
    token = request_id_ctx.set(trace_id)

    user_id: int = payload["user_id"]
    scan_tag: str = payload.get("tag", "scan")

    async def _run() -> None:
        from app.db.models.quest import Quest
        async with session_context() as session:
            # Load active quests that match this scan
            quests_result = await session.execute(
                select(Quest).where(
                    Quest.is_active.is_(True),
                    Quest.condition_tag.in_([scan_tag, None]),
                )
            )
            quests = list(quests_result.scalars().all())
            if not quests:
                return

            quest_ids = [q.id for q in quests]

            # Load existing UserQuest rows (for update)
            uq_result = await session.execute(
                    select(UserQuestModel).where(
                    UserQuestModel.user_id == user_id,
                    UserQuestModel.quest_id.in_(quest_ids),
                )
            )
            existing: dict[str, UserQuest] = {uq.quest_id: uq for uq in uq_result.scalars().all()}

            newly_completed: list[Quest] = []

            for quest in quests:
                uq = existing.get(quest.id)

                if uq is None:
                    uq = UserQuest(user_id=user_id, quest_id=quest.id, progress=0)
                    session.add(uq)

                if uq.completed_at is not None:
                    continue  # already done

                uq.progress += 1

                if uq.progress >= quest.target_count:
                    uq.completed_at = datetime.now(UTC)
                    newly_completed.append(quest)

            await session.commit()

        # Emit quest_completed outbox events for each newly completed quest
        if newly_completed:
            for quest in newly_completed:
                event_dispatcher.emit(
                    "quest_completed",
                    {
                        "user_id": user_id,
                        "quest_id": quest.id,
                        "quest_name": quest.name,
                        "reward_xp": quest.reward_xp,
                        "request_id": trace_id,
                    },
                )
                logger.info(
                    "Quest %s completed by user %s.", quest.id, user_id
                )

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("Error in process_quest_progress for user %s: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=5) from exc
    finally:
        from app.core.logger import request_id_ctx as ctx
        ctx.reset(token)


# ──────────────────────────────────────────────────────────────────────────────
# Achievement Check Worker
# ──────────────────────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, queue="progress.commands")
def process_achievement_check(self, payload: dict) -> None:
    """Check and unlock achievements for a user after a qualifying action.

    Evaluates all unearned achievements against their conditions and
    unlocks any that are now satisfied.
    """
    from app.core.logger import request_id_ctx

    trace_id = payload.get("request_id") or str(uuid.uuid4())
    token = request_id_ctx.set(trace_id)

    user_id: int = payload["user_id"]

    async def _run() -> None:
        from app.db.models.achievement import Achievement, UserAchievement
        from app.db.models.achievement_condition import (
            AchievementCondition,
            AchievementConditionType,
        )
        from app.db.models.validation import Validation
        from app.db.models.xp_event import XpEvent
        from app.db.models.user_quest import UserQuest
        from app.services.user import UserService

        async with session_context() as session:
            # Load user
            user_svc = UserService(session)
            user = await user_svc.get_user_by_id(user_id)
            if user is None:
                return

            # Load all achievements not yet unlocked for this user
            locked_result = await session.execute(
                select(Achievement, UserAchievement)
                .outerjoin(
                    UserAchievement,
                    (UserAchievement.achievement_id == Achievement.id)
                    & (UserAchievement.user_id == user_id),
                )
                .where(
                    (UserAchievement.id.is_(None))
                    | (UserAchievement.unlocked.is_(False))
                )
            )
            rows = list(locked_result.all())

            if not rows:
                return

            # Pre-compute user stats (cheap, single-pass)
            scan_count = (
                await session.execute(
                    select(func.count()).select_from(Validation).where(
                        Validation.user_id == user_id
                    )
                )
            ).scalar_one()

            xp_total = user.xp or 0
            level = user.level or 1
            streak = user.streak_days or 0

            completed_quests = (
                await session.execute(
                    select(func.count()).select_from(UserQuest).where(
                        UserQuest.user_id == user_id,
                        UserQuest.completed_at.is_not(None),
                    )
                )
            ).scalar_one()

            # Load conditions for all relevant achievements
            achievement_ids = [row[0].id for row in rows]
            cond_result = await session.execute(
                select(AchievementCondition).where(
                    AchievementCondition.achievement_id.in_(achievement_ids)
                )
            )
            conditions: dict[str, list[AchievementCondition]] = {}
            for cond in cond_result.scalars().all():
                conditions.setdefault(cond.achievement_id, []).append(cond)

            newly_unlocked: list[tuple[Achievement, int]] = []

            for achievement, user_achievement in rows:
                if user_achievement and user_achievement.unlocked:
                    continue

                achiev_conditions = conditions.get(achievement.id, [])
                if not achiev_conditions:
                    continue  # no conditions defined → skip

                # All conditions must be satisfied (AND logic)
                all_met = True
                for cond in achiev_conditions:
                    if cond.condition_type == AchievementConditionType.SCAN_COUNT:
                        all_met = scan_count >= cond.threshold
                    elif cond.condition_type == AchievementConditionType.XP_TOTAL:
                        all_met = xp_total >= cond.threshold
                    elif cond.condition_type == AchievementConditionType.LEVEL_REACHED:
                        all_met = level >= cond.threshold
                    elif cond.condition_type == AchievementConditionType.STREAK_DAYS:
                        all_met = streak >= cond.threshold
                    elif cond.condition_type == AchievementConditionType.QUEST_COUNT:
                        all_met = completed_quests >= cond.threshold
                    else:
                        all_met = False  # unknown condition type → skip

                    if not all_met:
                        break

                if not all_met:
                    continue

                # Unlock!
                now = datetime.now(UTC)
                if user_achievement is None:
                    ua = UserAchievement(
                        user_id=user_id,
                        achievement_id=achievement.id,
                        unlocked=True,
                        progress_percent=100,
                        unlocked_at=now,
                    )
                    session.add(ua)
                else:
                    user_achievement.unlocked = True
                    user_achievement.progress_percent = 100
                    user_achievement.unlocked_at = now
                    session.add(user_achievement)

                # Grant XP for the achievement
                xp = achievement.reward_xp
                if xp > 0:
                    source = f"achievement:{user_id}:{achievement.id}"
                    from app.db.models.xp_event import XpEvent
                    from app.db.models.enums import UIColorToken

                    # Check idempotency via source uniqueness
                    existing_xp_event = (
                        await session.execute(
                            select(XpEvent).where(
                                XpEvent.user_id == user_id,
                                XpEvent.source == source,
                            ).limit(1)
                        )
                    ).scalar_one_or_none()

                    if existing_xp_event is None:
                        xp_event = XpEvent(
                            user_id=user_id,
                            xp=xp,
                            source=source,
                            tag="achievement",
                            color=UIColorToken.GOLD,
                            occurred_at=now,
                        )
                        session.add(xp_event)
                        user.xp = (user.xp or 0) + xp
                        session.add(user)

                newly_unlocked.append((achievement, xp))

            await session.commit()

        # Fire SSE notifications
        if newly_unlocked:
            for achievement, xp in newly_unlocked:
                event_dispatcher.emit(
                    "achievement_unlocked",
                    {
                        "user_id": user_id,
                        "achievement_id": achievement.id,
                        "name": achievement.name,
                        "xp": xp,
                        "rarity": achievement.rarity.value if achievement.rarity else "common",
                        "request_id": trace_id,
                    },
                )
                logger.info(
                    "Achievement %s unlocked for user %s (+%s XP).",
                    achievement.id,
                    user_id,
                    xp,
                )

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.error("Error in process_achievement_check for user %s: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=5) from exc
    finally:
        from app.core.logger import request_id_ctx as ctx
        ctx.reset(token)


process_achievement_progress = process_achievement_check


# ──────────────────────────────────────────────────────────────────────────────
# Collection Progress Worker
# ──────────────────────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, queue="progress.commands")
def process_collection_progress(self, payload: dict) -> None:
    """Check if the user has completed any collection after a new scan/item award.

    A collection is complete when the user has acquired all items in it.
    Acquisition is determined by Validation records.
    """
    from app.core.logger import request_id_ctx

    trace_id = payload.get("request_id") or str(uuid.uuid4())
    token = request_id_ctx.set(trace_id)

    user_id: int = payload["user_id"]
    item_id: int | None = payload.get("item_id")

    async def _run() -> None:
        from app.db.models.collection import Collection, CollectionItem, UserCollection
        from app.db.models.validation import Validation

        async with session_context() as session:
            # Only check collections that contain the just-awarded item
            if item_id is None:
                return

            col_result = await session.execute(
                select(Collection)
                .join(CollectionItem, CollectionItem.collection_id == Collection.id)
                .where(
                    Collection.is_active.is_(True),
                    CollectionItem.item_id == item_id,
                )
            )
            collections = list(col_result.scalars().all())
            if not collections:
                return

            # Load user's already-completed collections
            uc_result = await session.execute(
                select(UserCollection).where(
                    UserCollection.user_id == user_id,
                    UserCollection.collection_id.in_([c.id for c in collections]),
                    UserCollection.completed_at.is_not(None),
                )
            )
            completed_ids = {uc.collection_id for uc in uc_result.scalars().all()}

            # Get all items user has acquired (via Validations)
            user_items_result = await session.execute(
                select(Validation.item_id).where(Validation.user_id == user_id)
            )
            user_item_ids: set[int] = set(user_items_result.scalars().all())

            newly_completed: list[Collection] = []

            for collection in collections:
                if collection.id in completed_ids:
                    continue

                # Load all required item IDs for this collection
                req_result = await session.execute(
                    select(CollectionItem.item_id).where(
                        CollectionItem.collection_id == collection.id
                    )
                )
                required = set(req_result.scalars().all())

                if not required.issubset(user_item_ids):
                    continue  # not yet complete

                # Mark complete
                now = datetime.now(UTC)
                uc_result2 = await session.execute(
                    select(UserCollection).where(
                        UserCollection.user_id == user_id,
                        UserCollection.collection_id == collection.id,
                    )
                )
                uc = uc_result2.scalar_one_or_none()
                if uc is None:
                    uc = UserCollection(
                        user_id=user_id,
                        collection_id=collection.id,
                        completed_at=now,
                    )
                    session.add(uc)
                else:
                    uc.completed_at = now
                    session.add(uc)

                newly_completed.append(collection)

            await session.commit()

        if newly_completed:
            from app.core.events import event_dispatcher

            for collection in newly_completed:
                event_dispatcher.emit(
                    "collection_completed",
                    {
                        "user_id": user_id,
                        "collection_id": collection.id,
                        "name": collection.name,
                        "request_id": trace_id,
                    },
                )
            logger.info(
                "User %s completed %d collection(s): %s",
                user_id,
                len(newly_completed),
                [c.id for c in newly_completed],
            )

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.error("Error in process_collection_progress for user %s: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=5) from exc
    finally:
        from app.core.logger import request_id_ctx as ctx
        ctx.reset(token)
