from fastapi import APIRouter

from app.api.v1.dependencies import CurrentUser
from app.schemas.frontend import QuestsResponse
from app.services.business.frontend_data import FrontendDataBusinessService

router = APIRouter(prefix="/quests", tags=["Quest"])


@router.get("", response_model=QuestsResponse)
async def get_quests(current_user: CurrentUser):
    return await FrontendDataBusinessService().get_quests(current_user=current_user)
