from sqlalchemy import select

from app.db.models.user_quest import UserQuest
from app.db.repositories.base import BaseRepository


class UserQuestRepository(BaseRepository[UserQuest]):
    model = UserQuest

    async def get_for_user_and_quests(
        self,
        *,
        user_id: int,
        quest_ids: list[str],
    ) -> list[UserQuest]:
        if not quest_ids:
            return []
        result = await self.session.execute(
            select(UserQuest).where(
                UserQuest.user_id == user_id,
                UserQuest.quest_id.in_(quest_ids),
            )
        )
        return list(result.scalars().all())

    async def get_for_user_and_quest(
        self,
        *,
        user_id: int,
        quest_id: str,
    ) -> UserQuest | None:
        result = await self.session.execute(
            select(UserQuest)
            .where(UserQuest.user_id == user_id, UserQuest.quest_id == quest_id)
            .limit(1)
        )
        return result.scalar_one_or_none()
