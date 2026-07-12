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

    async def get_active_map_secrets(self) -> list[ItemSecret]:
        from datetime import datetime, UTC
        now_utc = datetime.now(UTC)
        query = (
            select(ItemSecret)
            .where(
                ItemSecret.is_active.is_(True),
                ItemSecret.latitude.is_not(None),
                ItemSecret.longitude.is_not(None),
                (ItemSecret.cooldown_until.is_(None) | (ItemSecret.cooldown_until < now_utc)),
            )
            .order_by(ItemSecret.title.asc(), ItemSecret.id.asc())
        )

        result = await self.session.execute(query)

        return list(result.scalars().all())

    async def get_active_map_secret_by_id(
        self,
        secret_id: int,
    ) -> ItemSecret | None:
        from datetime import datetime, UTC
        now_utc = datetime.now(UTC)
        query = (
            select(ItemSecret)
            .where(
                ItemSecret.id == secret_id,
                ItemSecret.is_active.is_(True),
                ItemSecret.latitude.is_not(None),
                ItemSecret.longitude.is_not(None),
                (ItemSecret.cooldown_until.is_(None) | (ItemSecret.cooldown_until < now_utc)),
            )
            .limit(1)
        )

        result = await self.session.execute(query)

        return result.scalar_one_or_none()
