from sqlalchemy import select

from app.db.models.quest import Quest
from app.db.repositories.base import BaseRepository


class QuestRepository(BaseRepository[Quest]):
    model = Quest

    async def get_active_quests(self) -> list[Quest]:
        query = (
            select(Quest)
            .where(Quest.is_active.is_(True))
            .order_by(Quest.rarity.asc(), Quest.name.asc())
        )

        result = await self.session.execute(query)

        return list(result.scalars().all())
