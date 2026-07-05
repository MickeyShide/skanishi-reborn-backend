from fastapi import APIRouter, Request

from app.schemas.frontend import QuestsResponse
from app.services.business.frontend_data import FrontendDataBusinessService

router = APIRouter(prefix="/quests", tags=["Quest"])


@router.get("", response_model=QuestsResponse)
async def get_quests(request: Request):
    return await FrontendDataBusinessService(request=request).get_quests()
