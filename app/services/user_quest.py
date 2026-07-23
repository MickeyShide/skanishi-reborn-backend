from app.db.models.user_quest import UserQuest
from app.db.repositories.user_quest import UserQuestRepository
from app.services.base import BaseService


class UserQuestService(BaseService):
    repositories = {"user_quest_repository": UserQuestRepository}

    user_quest_repository: UserQuestRepository

    async def get_for_user_and_quests(
        self,
        *,
        user_id: int,
        quest_ids: list[str],
    ) -> list[UserQuest]:
        return await self.user_quest_repository.get_for_user_and_quests(
            user_id=user_id,
            quest_ids=quest_ids,
        )

    async def get_for_user_and_quest(
        self,
        *,
        user_id: int,
        quest_id: str,
    ) -> UserQuest | None:
        return await self.user_quest_repository.get_for_user_and_quest(
            user_id=user_id,
            quest_id=quest_id,
        )

    async def mark_reward_claimed(self, user_quest: UserQuest) -> UserQuest:
        return await self.user_quest_repository.update(user_quest, reward_claimed=True)
