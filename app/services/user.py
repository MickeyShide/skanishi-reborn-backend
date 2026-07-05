# app/services/user.py

from __future__ import annotations

from app.db.models.user import User, UserRole
from app.db.repositories.user import UserRepository
from app.services.base import BaseService
from app.services.init_data import TelegramUserData


class UserService(BaseService):
    repositories = {
        "user_repository": UserRepository,
    }

    user_repository: UserRepository

    async def get_user_by_id(self, user_id: int) -> User:
        return await self.user_repository.get_by_id(user_id)

    async def get_user_by_tg_id(self, tg_id: int) -> User | None:
        return await self.user_repository.get_one_or_none(tg_id=tg_id)

    async def create_from_telegram(
        self,
        telegram_user: TelegramUserData,
    ) -> User:
        return await self.user_repository.create(
            tg_id=telegram_user.tg_id,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            username=telegram_user.username,
            is_premium=telegram_user.is_premium or False,
            photo_url=telegram_user.photo_url,
            is_private=True,
            role=UserRole.USER,
        )

    async def update_telegram_fields(
        self,
        user: User,
        telegram_user: TelegramUserData,
    ) -> User:
        return await self.user_repository.update(
            user,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            username=telegram_user.username,
            is_premium=telegram_user.is_premium or False,
            photo_url=telegram_user.photo_url,
        )

    async def get_or_create_from_telegram(
        self,
        telegram_user: TelegramUserData,
    ) -> User:
        user = await self.get_user_by_tg_id(telegram_user.tg_id)

        if user is None:
            return await self.create_from_telegram(telegram_user)

        return await self.update_telegram_fields(
            user=user,
            telegram_user=telegram_user,
        )

    async def update_privacy(
        self,
        user: User,
        *,
        is_private: bool,
    ) -> User:
        return await self.user_repository.update(
            user,
            is_private=is_private,
        )

    async def apply_scan_reward(
        self,
        user: User,
        *,
        reward_xp: int,
    ) -> User:
        next_level_xp = max(user.next_level_xp, 0)
        new_xp = user.xp + reward_xp

        if next_level_xp > 0:
            clamped_xp = min(new_xp, next_level_xp)
            level_progress = min(100, int((clamped_xp / next_level_xp) * 100))
        else:
            clamped_xp = new_xp
            level_progress = 0

        return await self.user_repository.update(
            user,
            xp=clamped_xp,
            level_progress=level_progress,
        )
