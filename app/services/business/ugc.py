from __future__ import annotations

from collections.abc import Callable

from app.db.models.user import User
from app.db.models.user_stickers import UserSticker
from app.services.business.base import BusinessService
from app.services.errors import StickerAlreadyExistsError, StickerNotFoundError
from app.services.ugc import UGCService


class UGCBusinessService(BusinessService):
    ugc_service: UGCService

    async def get_my_sticker(self, current_user: User) -> UserSticker:
        sticker = await self.ugc_service.get_user_sticker(
            user_id=current_user.id
        )

        if sticker is None:
            raise StickerNotFoundError()

        return sticker

    async def generate_my_sticker(
        self,
        current_user: User,
        token_factory: Callable[[], str],
    ) -> UserSticker:
        existing_sticker = await self.ugc_service.get_user_sticker(
            user_id=current_user.id
        )
        if existing_sticker is not None:
            raise StickerAlreadyExistsError()

        return await self.ugc_service.create_sticker(
            user_id=current_user.id,
            token=token_factory(),
        )
