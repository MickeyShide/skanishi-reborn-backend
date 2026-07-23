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

    async def get_referral_contacts(
        self,
        *,
        referrer_id: int,
        limit: int,
    ) -> list[tuple[str | None, str | None]]:
        query = (
            select(User.first_name, User.username)
            .where(User.referred_by_id == referrer_id)
            .order_by(User.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.all())

    async def get_public_leaderboard(
        self,
        *,
        limit: int,
        offset: int,
    ) -> list[User]:
        query = (
            select(User)
            .where(User.is_private.is_(False))
            .order_by(User.rank.asc(), User.id.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
