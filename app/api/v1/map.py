from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import CurrentUser

from app.config import settings
from app.schemas.common import MapPointsQueryParams
from app.schemas.frontend import MapPointsResponse
from app.services.business.frontend_data import FrontendDataBusinessService

router = APIRouter(prefix="/map", tags=["Map"])


@router.get("/points", response_model=MapPointsResponse)
async def get_map_points(
    current_user: CurrentUser,
    params: Annotated[MapPointsQueryParams, Depends()],
):
    return await FrontendDataBusinessService().get_map_points(
        current_user=current_user,
        params=params
    )
