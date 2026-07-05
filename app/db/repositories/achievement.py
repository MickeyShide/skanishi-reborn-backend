from sqlalchemy import and_, func, select

from app.db.models.achievement import Achievement, UserAchievement
from app.db.repositories.base import BaseRepository

type AchievementStateRow = tuple[Achievement, UserAchievement | None]


class AchievementRepository(BaseRepository[Achievement]):
    model = Achievement

    async def get_user_achievement_states(
        self,
        *,
        user_id: int,
    ) -> list[AchievementStateRow]:
        query = (
            select(Achievement, UserAchievement)
            .outerjoin(
                UserAchievement,
                and_(
                    UserAchievement.achievement_id == Achievement.id,
                    UserAchievement.user_id == user_id,
                ),
            )
            .order_by(Achievement.name.asc())
        )

        result = await self.session.execute(query)

        return list(result.all())

    async def count_total_achievements(self) -> int:
        query = select(func.count()).select_from(Achievement)

        result = await self.session.execute(query)

        return int(result.scalar_one())
