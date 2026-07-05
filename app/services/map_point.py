from app.db.models.enums import Rarity
from app.db.models.map_point import MapPoint
from app.db.repositories.map_point import MapPointRepository
from app.services.base import BaseService


class MapPointService(BaseService):
    repositories = {
        "map_point_repository": MapPointRepository,
    }

    map_point_repository: MapPointRepository

    async def get_active_points(
        self,
        *,
        rarity: Rarity | None = None,
        category: str | None = None,
    ) -> list[MapPoint]:
        return await self.map_point_repository.get_active_points(
            rarity=rarity,
            category=category,
        )

    async def get_active_point_by_id(self, point_id: str) -> MapPoint | None:
        return await self.map_point_repository.get_active_point_by_id(point_id)
