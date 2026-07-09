from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.db.models.event import Event, EventGoal, EventItem, EventModifier, UserEvent
from app.db.models.user import User
from app.schemas.frontend import FrontendUserResponse
from app.services.business.base import BusinessService


class EventModifierResponse(EventModifier):
    pass


class EventItemResponse(EventItem):
    pass


class EventGoalResponse(EventGoal):
    progress: int = 0
    is_completed: bool = False
    reward_claimed: bool = False


class EventDetailResponse(Event):
    modifiers: list[EventModifierResponse] = []
    items: list[EventItemResponse] = []
    goals: list[EventGoalResponse] = []


class EventBusinessService(BusinessService):
    """Business service for retrieving events and user progress."""

    async def get_active_events(self, current_user: User) -> list[EventDetailResponse]:
        """Return all active events with modifiers, items, goals, and user progress."""
        session = await self._get_session()
        now = datetime.now(UTC)

        # 1. Fetch active events
        events_result = await session.execute(
            select(Event).where(
                Event.is_active.is_(True),
                Event.starts_at <= now,
                Event.ends_at >= now,
            )
        )
        events = list(events_result.scalars().all())
        if not events:
            return []

        event_ids = [e.id for e in events]

        # 2. Fetch modifiers
        mod_result = await session.execute(
            select(EventModifier).where(EventModifier.event_id.in_(event_ids))
        )
        modifiers_by_event = {}
        for mod in mod_result.scalars().all():
            modifiers_by_event.setdefault(mod.event_id, []).append(EventModifierResponse(**mod.model_dump()))

        # 3. Fetch items
        items_result = await session.execute(
            select(EventItem).where(EventItem.event_id.in_(event_ids))
        )
        items_by_event = {}
        for item in items_result.scalars().all():
            items_by_event.setdefault(item.event_id, []).append(EventItemResponse(**item.model_dump()))

        # 4. Fetch goals
        goals_result = await session.execute(
            select(EventGoal).where(EventGoal.event_id.in_(event_ids))
        )
        goals_by_event = {}
        all_goals = list(goals_result.scalars().all())
        for goal in all_goals:
            goals_by_event.setdefault(goal.event_id, []).append(goal)

        # 5. Fetch UserEvents (progress)
        user_events_result = await session.execute(
            select(UserEvent).where(
                UserEvent.user_id == current_user.id,
                UserEvent.event_id.in_(event_ids),
            )
        )
        user_events = {(ue.event_id, ue.goal_id): ue for ue in user_events_result.scalars().all()}

        # 6. Assemble responses
        responses = []
        for event in events:
            event_goals = []
            for goal in goals_by_event.get(event.id, []):
                ue = user_events.get((event.id, goal.id))
                progress = ue.progress if ue else 0
                is_completed = ue.completed_at is not None if ue else False
                reward_claimed = ue.reward_claimed if ue else False

                event_goals.append(
                    EventGoalResponse(
                        **goal.model_dump(),
                        progress=progress,
                        is_completed=is_completed,
                        reward_claimed=reward_claimed,
                    )
                )

            responses.append(
                EventDetailResponse(
                    **event.model_dump(),
                    modifiers=modifiers_by_event.get(event.id, []),
                    items=items_by_event.get(event.id, []),
                    goals=event_goals,
                )
            )

        return responses

    async def claim_goal_reward(self, current_user: User, event_id: str, goal_id: str) -> FrontendUserResponse:
        """Claim the reward for a completed event goal."""
        from app.db.models.enums import UIColorToken
        from app.db.models.xp_event import XpEvent
        from app.services.errors import ForbiddenError, ItemNotFoundError, RewardAlreadyClaimedError
        from app.services.user import UserService
        from app.services.business.daily_and_quests import _build_user_response

        session = await self._get_session()

        ue_result = await session.execute(
            select(UserEvent).where(
                UserEvent.user_id == current_user.id,
                UserEvent.event_id == event_id,
                UserEvent.goal_id == goal_id,
            )
        )
        ue = ue_result.scalar_one_or_none()

        if not ue or not ue.completed_at:
            raise ForbiddenError("Goal is not completed yet.")

        if ue.reward_claimed:
            raise RewardAlreadyClaimedError("Goal reward already claimed.")

        goal = await session.get(EventGoal, goal_id)
        if not goal:
            raise ItemNotFoundError("Goal not found.")

        # Grant XP
        xp = goal.reward_xp
        source = f"event_goal:{current_user.id}:{event_id}:{goal_id}"

        existing = (
            await session.execute(
                select(XpEvent).where(
                    XpEvent.user_id == current_user.id,
                    XpEvent.source == source,
                ).limit(1)
            )
        ).scalar_one_or_none()

        updated_user = current_user
        if not existing and xp > 0:
            xp_event = XpEvent(
                user_id=current_user.id,
                xp=xp,
                source=source,
                tag="event",
                color=UIColorToken.PINK,
                occurred_at=datetime.now(UTC),
            )
            session.add(xp_event)
            
            user_svc = UserService(session)
            updated_user = await user_svc.add_xp_and_check_level_up(current_user, xp)

        ue.reward_claimed = True
        session.add(ue)

        return _build_user_response(updated_user)
