from app.db.repositories.achievement import AchievementRepository, AchievementStateRow
from app.services.base import BaseService


class AchievementService(BaseService):
    repositories = {
        "achievement_repository": AchievementRepository,
    }

    achievement_repository: AchievementRepository

    async def get_user_achievement_states(
        self,
        *,
        user_id: int,
    ) -> list[AchievementStateRow]:
        return await self.achievement_repository.get_user_achievement_states(
            user_id=user_id
        )

    async def count_total_achievements(self) -> int:
        return await self.achievement_repository.count_total_achievements()
