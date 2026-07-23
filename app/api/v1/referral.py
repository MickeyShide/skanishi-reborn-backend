from fastapi import APIRouter

from app.api.v1.dependencies import CurrentUser
from app.schemas.referral import ReferralStatsResponse
from app.services.business.referral import ReferralBusinessService

router = APIRouter(prefix="/referrals", tags=["Referrals"])


@router.get("/me", response_model=ReferralStatsResponse)
async def get_my_referrals(current_user: CurrentUser) -> ReferralStatsResponse:
    return await ReferralBusinessService().get_my_referrals(current_user)
