from app.db.models.quest import Quest
from app.db.repositories.quest import QuestRepository
from app.services.base import BaseService


class QuestService(BaseService):
    repositories = {
        "quest_repository": QuestRepository,
    }

    quest_repository: QuestRepository

    async def get_active_quests(self) -> list[Quest]:
        return await self.quest_repository.get_active_quests()

    async def get_quest(self, quest_id: str) -> Quest | None:
        return await self.quest_repository.get_by_quest_id(quest_id)
