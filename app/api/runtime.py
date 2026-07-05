from fastapi import APIRouter

from app.config import settings
from app.schemas.settings import MapApiKeyResponse
from app.services.errors import MapApiKeyNotConfiguredError

router = APIRouter(tags=["Runtime"])


@router.get("/map/api-key", response_model=MapApiKeyResponse)
async def get_map_api_key():
    api_key = settings.YANDEX_MAPS_API_KEY
    if api_key is None or not api_key.strip():
        raise MapApiKeyNotConfiguredError()

    return MapApiKeyResponse(api_key=api_key)
