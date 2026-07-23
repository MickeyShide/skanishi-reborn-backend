from app.config import settings
from app.db.models.user import User
from app.schemas.referral import ReferralStatsResponse
from app.services.business.base import BusinessService
from app.services.errors import ServiceNotReadyError
from app.services.user import UserService


class ReferralBusinessService(BusinessService):
    user_service: UserService

    async def get_my_referrals(self, current_user: User) -> ReferralStatsResponse:
        bot_username = settings.TELEGRAM_BOT_USERNAME
        if not bot_username:
            raise ServiceNotReadyError("Telegram bot username is not configured.")

        referral_contacts = await self.user_service.get_referral_contacts(
            referrer_id=current_user.id,
            limit=50,
        )
        friends = [
            first_name or username or "Охотник"
            for first_name, username in referral_contacts
        ]

        return ReferralStatsResponse(
            referral_link=(
                f"https://t.me/{bot_username}/app?startapp=ref_{current_user.id}"
            ),
            total_friends=len(friends),
            friends_list=friends,
        )
