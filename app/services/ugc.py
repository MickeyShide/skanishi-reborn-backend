from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.db.models.user_stickers import UserSticker, UserStickerScan
from app.db.repositories.user_sticker import (
    UserStickerRepository,
    UserStickerScanRepository,
)
from app.services.base import BaseService
from app.services.errors import StickerAlreadyExistsError


class UGCService(BaseService):
    repositories = {
        "user_sticker_repository": UserStickerRepository,
        "user_sticker_scan_repository": UserStickerScanRepository,
    }

    user_sticker_repository: UserStickerRepository
    user_sticker_scan_repository: UserStickerScanRepository

    async def get_user_sticker(self, *, user_id: int) -> UserSticker | None:
        return await self.user_sticker_repository.get_by_user_id(user_id=user_id)

    async def get_active_sticker_by_token(self, *, token: str) -> UserSticker | None:
        return await self.user_sticker_repository.get_active_by_token(token=token)

    async def create_sticker(self, *, user_id: int, token: str) -> UserSticker:
        try:
            return await self.user_sticker_repository.create(
                user_id=user_id,
                token=token,
            )
        except IntegrityError as exc:
            raise StickerAlreadyExistsError() from exc

    async def has_user_scanned_sticker(
        self,
        *,
        user_id: int,
        sticker_id: int,
    ) -> bool:
        scan = await self.user_sticker_scan_repository.get_by_user_and_sticker(
            user_id=user_id,
            sticker_id=sticker_id,
        )
        return scan is not None

    async def record_scan(self, *, user_id: int, sticker_id: int) -> UserStickerScan:
        return await self.user_sticker_scan_repository.create(
            user_id=user_id,
            sticker_id=sticker_id,
        )

    async def increment_scan_count(self, sticker: UserSticker) -> UserSticker:
        return await self.user_sticker_repository.update(
            sticker,
            scan_count=sticker.scan_count + 1,
        )
