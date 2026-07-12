from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select

from app.db.models.user import User
from app.db.models.user_stickers import UserSticker
from app.services.business.base import BusinessService


class UGCBusinessService(BusinessService):
    async def get_my_sticker(self, current_user: User) -> UserSticker:
        session = await self._get_session()
        sticker_result = await session.execute(
            select(UserSticker).where(UserSticker.user_id == current_user.id)
        )
        sticker = sticker_result.scalar_one_or_none()

        if sticker is None:
            raise ValueError("sticker_not_found")

        return sticker

    async def generate_my_sticker(
        self,
        current_user: User,
        token_factory: Callable[[], str],
    ) -> UserSticker:
        session = await self._get_session()
        sticker_result = await session.execute(
            select(UserSticker).where(UserSticker.user_id == current_user.id)
        )
        existing_sticker = sticker_result.scalar_one_or_none()

        if existing_sticker is not None:
            raise ValueError("sticker_already_exists")

        new_sticker = UserSticker(
            user_id=current_user.id,
            token=token_factory(),
        )
        session.add(new_sticker)
        await session.flush()

        return new_sticker
