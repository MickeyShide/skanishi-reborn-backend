from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.schemas.common import MapPointsQueryParams
from app.schemas.frontend import MapPointsResponse
from app.schemas.settings import MapApiKeyResponse
from app.services.business.frontend_data import FrontendDataBusinessService
from app.services.errors import MapApiKeyNotConfiguredError

router = APIRouter(prefix="/map", tags=["Map"])


@router.get("/api-key", response_model=MapApiKeyResponse)
async def get_map_api_key():
    api_key = settings.YANDEX_MAPS_API_KEY
    if api_key is None or not api_key.strip():
        raise MapApiKeyNotConfiguredError()

    return MapApiKeyResponse(api_key=api_key)


@router.get("/points", response_model=MapPointsResponse)
async def get_map_points(
    request: Request,
    params: Annotated[MapPointsQueryParams, Depends()],
):
    return await FrontendDataBusinessService(request=request).get_map_points(
        params=params
    )
