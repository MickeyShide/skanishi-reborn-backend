from sqlalchemy import select

from app.db.models.user_stickers import UserSticker, UserStickerScan
from app.db.repositories.base import BaseRepository


class UserStickerRepository(BaseRepository[UserSticker]):
    model = UserSticker

    async def get_by_user_id(self, *, user_id: int) -> UserSticker | None:
        result = await self.session.execute(
            select(UserSticker).where(UserSticker.user_id == user_id).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_active_by_token(self, *, token: str) -> UserSticker | None:
        result = await self.session.execute(
            select(UserSticker)
            .where(UserSticker.token == token, UserSticker.is_active.is_(True))
            .limit(1)
        )
        return result.scalar_one_or_none()


class UserStickerScanRepository(BaseRepository[UserStickerScan]):
    model = UserStickerScan

    async def get_by_user_and_sticker(
        self,
        *,
        user_id: int,
        sticker_id: int,
    ) -> UserStickerScan | None:
        result = await self.session.execute(
            select(UserStickerScan)
            .where(
                UserStickerScan.user_id == user_id,
                UserStickerScan.sticker_id == sticker_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
