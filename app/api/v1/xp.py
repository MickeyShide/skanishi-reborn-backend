from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import CurrentUser

from app.schemas.common import XpHistoryQueryParams
from app.schemas.frontend import XpHistoryResponse
from app.services.business.frontend_data import FrontendDataBusinessService

router = APIRouter(prefix="/xp", tags=["XP"])


@router.get("/history", response_model=XpHistoryResponse)
async def get_xp_history(
    current_user: CurrentUser,
    params: Annotated[XpHistoryQueryParams, Depends()],
) -> XpHistoryResponse:
    return await FrontendDataBusinessService().get_xp_history(
        current_user=current_user,
        params=params,
    )
