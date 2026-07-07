import hashlib
from datetime import UTC, datetime

from app.db.models.item_secrets import ItemSecret
from app.db.repositories.item_secret import ItemSecretRepository
from app.services.base import BaseService


class ItemSecretService(BaseService):
    repositories = {
        "item_secret_repository": ItemSecretRepository,
    }

    item_secret_repository: ItemSecretRepository

    @staticmethod
    def hash_secret(secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    async def get_active_by_secret_hash(self, secret_hash: str) -> ItemSecret | None:
        item_secret = await self.item_secret_repository.get_active_by_secret_hash(
            secret_hash
        )
        if item_secret is None:
            return None

        if (
            item_secret.expires_at is not None
            and item_secret.expires_at <= datetime.now(UTC)
        ):
            return None

        return item_secret

    async def get_active_map_secrets(self) -> list[ItemSecret]:
        return await self.item_secret_repository.get_active_map_secrets()

    async def get_active_map_secret_by_id(
        self,
        secret_id: int,
    ) -> ItemSecret | None:
        return await self.item_secret_repository.get_active_map_secret_by_id(
            secret_id
        )
