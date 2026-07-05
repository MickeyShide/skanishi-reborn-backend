from fastapi import APIRouter, Request

from app.schemas.frontend import AchievementsResponse
from app.services.business.frontend_data import FrontendDataBusinessService

router = APIRouter(prefix="/achievements", tags=["Achievement"])


@router.get("", response_model=AchievementsResponse)
async def get_achievements(request: Request):
    return await FrontendDataBusinessService(request=request).get_achievements()
