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
