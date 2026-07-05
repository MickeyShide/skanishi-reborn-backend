from fastapi import APIRouter, Request

from app.schemas.frontend import FrontendAppStateResponse
from app.services.business.frontend_data import FrontendDataBusinessService

router = APIRouter(prefix="/app", tags=["App"])


@router.get("/state", response_model=FrontendAppStateResponse)
async def get_app_state(request: Request):
    return await FrontendDataBusinessService(request=request).get_app_state()
