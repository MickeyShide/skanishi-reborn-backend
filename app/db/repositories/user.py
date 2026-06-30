from sqlalchemy import select

from app.db.models.user import User
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_tg_id(self, tg_id: int) -> User | None:
        query = select(User).where(User.tg_id == tg_id)

        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    async def get_active_users(self) -> list[User]:
        query = select(User).where(User.is_active.is_(True))

        result = await self.session.execute(query)

        return list(result.scalars().all())
