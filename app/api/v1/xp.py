from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.schemas.common import XpHistoryQueryParams
from app.schemas.frontend import XpHistoryResponse
from app.services.business.frontend_data import FrontendDataBusinessService

router = APIRouter(prefix="/xp", tags=["XP"])


@router.get("/history", response_model=XpHistoryResponse)
async def get_xp_history(
    request: Request,
    params: Annotated[XpHistoryQueryParams, Depends()],
):
    return await FrontendDataBusinessService(request=request).get_xp_history(
        params=params
    )
