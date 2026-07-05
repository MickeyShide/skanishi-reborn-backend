from fastapi import APIRouter

from app.api.v1.dependencies import CurrentUser
from app.schemas.frontend import AchievementsResponse
from app.services.business.frontend_data import FrontendDataBusinessService

router = APIRouter(prefix="/achievements", tags=["Achievement"])


@router.get("", response_model=AchievementsResponse)
async def get_achievements(current_user: CurrentUser):
    return await FrontendDataBusinessService().get_achievements(current_user=current_user)
