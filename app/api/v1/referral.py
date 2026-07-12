from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select, func

from app.api.v1.dependencies import CurrentUser, DbSession
from app.db.models.user import User

router = APIRouter(prefix="/referrals", tags=["Referrals"])

class ReferralStatsResponse(BaseModel):
    referral_link: str
    total_friends: int
    friends_list: list[str]

@router.get("/me", response_model=ReferralStatsResponse)
async def get_my_referrals(
    current_user: CurrentUser,
    session: DbSession,
) -> ReferralStatsResponse:
    # 1. Generate referral link
    bot_username = "skanishi_bot" # ideally from config
    link = f"https://t.me/{bot_username}/app?startapp=ref_{current_user.id}"
    
    # 2. Get referred friends
    result = await session.execute(
        select(User.first_name, User.username)
        .where(User.referred_by_id == current_user.id)
        .order_by(User.created_at.desc())
        .limit(50)
    )
    
    friends = []
    for first_name, username in result:
        friends.append(first_name or username or "Охотник")
        
    return ReferralStatsResponse(
        referral_link=link,
        total_friends=len(friends),
        friends_list=friends,
    )
