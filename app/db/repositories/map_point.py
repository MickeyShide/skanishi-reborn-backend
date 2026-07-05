from sqlalchemy import select

from app.db.models.enums import Rarity
from app.db.models.map_point import MapPoint
from app.db.repositories.base import BaseRepository


class MapPointRepository(BaseRepository[MapPoint]):
    model = MapPoint

    async def get_active_points(
        self,
        *,
        rarity: Rarity | None = None,
        category: str | None = None,
    ) -> list[MapPoint]:
        query = select(MapPoint).where(MapPoint.is_active.is_(True))

        if rarity is not None:
            query = query.where(MapPoint.rarity == rarity)

        if category is not None:
            query = query.where(MapPoint.category == category)

        query = query.order_by(MapPoint.name.asc())

        result = await self.session.execute(query)

        return list(result.scalars().all())

    async def get_active_point_by_id(self, point_id: str) -> MapPoint | None:
        query = (
            select(MapPoint)
            .where(
                MapPoint.id == point_id,
                MapPoint.is_active.is_(True),
            )
            .limit(1)
        )

        result = await self.session.execute(query)

        return result.scalar_one_or_none()
