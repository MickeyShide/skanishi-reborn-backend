from fastapi import APIRouter

from app.api.v1.dependencies import CurrentUser
from app.schemas.frontend import FrontendAppStateResponse
from app.services.business.frontend_data import FrontendDataBusinessService

router = APIRouter(prefix="/app", tags=["App"])


@router.get("/state", response_model=FrontendAppStateResponse)
async def get_app_state(current_user: CurrentUser):
    return await FrontendDataBusinessService().get_app_state(current_user=current_user)
