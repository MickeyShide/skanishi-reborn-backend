# app/services/user.py
# app/services/user.py

from __future__ import annotations

from app.db.models.user import User, UserRole
from app.db.repositories.user import UserRepository
from app.services.base import BaseService
from app.services.init_data import TelegramUserData

LEVEL_THRESHOLDS = {
    1: 1000,
    2: 2500,
    3: 5000,
    4: 10000,
    5: 20000,
    6: 35000,
    7: 50000,
    8: 75000,
    9: 100000,
    10: 150000,
}

def get_next_level_xp(level: int) -> int:
    return LEVEL_THRESHOLDS.get(level, level * 15000 + 1000)


def coins_for_xp(added_xp: int) -> int:
    return max(1, added_xp // 2) if added_xp > 0 else 0


class UserService(BaseService):
    repositories = {
        "user_repository": UserRepository,
    }

    user_repository: UserRepository

    async def get_user_by_id(self, user_id: int) -> User:
        return await self.user_repository.get_by_id(user_id)

    async def add_fragment(self, user: User, rarity: str, amount: int) -> User:
        field = f"fragments_{rarity.lower()}"
        if not hasattr(user, field):
            return user
        return await self.user_repository.update(
            user,
            **{field: getattr(user, field) + amount},
        )

    async def get_user_by_tg_id(self, tg_id: int) -> User | None:
        return await self.user_repository.get_one_or_none(tg_id=tg_id)

    async def get_referral_contacts(
        self,
        *,
        referrer_id: int,
        limit: int,
    ) -> list[tuple[str | None, str | None]]:
        return await self.user_repository.get_referral_contacts(
            referrer_id=referrer_id,
            limit=limit,
        )

    async def get_public_leaderboard(
        self,
        *,
        limit: int,
        offset: int,
    ) -> list[User]:
        return await self.user_repository.get_public_leaderboard(
            limit=limit,
            offset=offset,
        )

    async def update_fields(self, user: User, **updates: object) -> User:
        return await self.user_repository.update(user, **updates)

    async def create_from_telegram(
        self,
        telegram_user: TelegramUserData,
        referred_by_id: int | None = None,
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
            next_level_xp=get_next_level_xp(1),
            referred_by_id=referred_by_id,
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
        referred_by_id: int | None = None,
    ) -> User:
        user, _ = await self.get_or_create_from_telegram_with_status(
            telegram_user,
            referred_by_id=referred_by_id,
        )
        return user

    async def get_or_create_from_telegram_with_status(
        self,
        telegram_user: TelegramUserData,
        referred_by_id: int | None = None,
    ) -> tuple[User, bool]:
        """Returns tuple (User, is_new)."""
        user = await self.get_user_by_tg_id(telegram_user.tg_id)

        if user is None:
            new_user = await self.create_from_telegram(telegram_user, referred_by_id=referred_by_id)
            return new_user, True

        updated_user = await self.update_telegram_fields(
            user=user,
            telegram_user=telegram_user,
        )
        return updated_user, False

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
        return await self.add_xp_and_check_level_up(user, reward_xp)

    async def add_xp_and_check_level_up(
        self,
        user: User,
        added_xp: int,
    ) -> User:
        new_xp = user.xp + added_xp
        current_coins = getattr(user, "coins", 0)
        new_coins = current_coins + coins_for_xp(added_xp)
        new_level = user.level
        next_level_xp = getattr(user, "next_level_xp", None) or get_next_level_xp(new_level)

        while new_xp >= next_level_xp:
            new_level += 1
            next_level_xp = get_next_level_xp(new_level)

        level_progress = min(100, int((new_xp / next_level_xp) * 100)) if next_level_xp > 0 else 0

        updates = {
            "xp": new_xp,
            "coins": new_coins,
            "level": new_level,
            "next_level_xp": next_level_xp,
            "level_progress": level_progress,
        }
        return await self.user_repository.update(user, **updates)
