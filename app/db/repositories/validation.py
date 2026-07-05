from sqlalchemy import func, select

from app.db.models.user import User
from app.db.models.validation import Validation
from app.db.repositories.base import BaseRepository

type ItemRatingRow = tuple[Validation, User]


class ValidationRepository(BaseRepository[Validation]):
    model = Validation

    async def get_user_item_ids(
        self,
        *,
        user_id: int,
        item_ids: list[int],
    ) -> set[int]:
        if not item_ids:
            return set()

        query = select(Validation.item_id).where(
            Validation.user_id == user_id,
            Validation.item_id.in_(item_ids),
        )

        result = await self.session.execute(query)

        return set(result.scalars().all())

    async def get_user_item_validation(
        self,
        *,
        user_id: int,
        item_id: int,
    ) -> Validation | None:
        query = (
            select(Validation)
            .where(
                Validation.user_id == user_id,
                Validation.item_id == item_id,
            )
            .limit(1)
        )

        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    async def get_item_rating_page(
        self,
        *,
        item_id: int,
        limit: int,
        offset: int,
    ) -> list[ItemRatingRow]:
        query = (
            select(Validation, User)
            .join(User, User.id == Validation.user_id)
            .where(Validation.item_id == item_id)
            .order_by(Validation.rank.asc(), Validation.id.asc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)

        return list(result.all())

    async def count_item_rating(self, *, item_id: int) -> int:
        query = select(func.count()).select_from(Validation).where(
            Validation.item_id == item_id
        )

        result = await self.session.execute(query)

        return int(result.scalar_one())

