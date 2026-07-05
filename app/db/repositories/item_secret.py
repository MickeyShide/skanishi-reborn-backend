from sqlalchemy import select

from app.db.models.item_secrets import ItemSecret
from app.db.repositories.base import BaseRepository


class ItemSecretRepository(BaseRepository[ItemSecret]):
    model = ItemSecret

    async def get_active_by_secret_hash(self, secret_hash: str) -> ItemSecret | None:
        query = (
            select(ItemSecret)
            .where(
                ItemSecret.secret_hash == secret_hash,
                ItemSecret.is_active.is_(True),
            )
            .limit(1)
        )

        result = await self.session.execute(query)

        return result.scalar_one_or_none()

