from fastapi import APIRouter, Request

from app.schemas.user import (
    UserPrivacySettingsResponse,
    UserPrivacySettingsUpdateRequest,
)
from app.services.business.user import UserBusinessService

router = APIRouter(prefix="/users", tags=["User"])


@router.get("/settings/privacy", response_model=UserPrivacySettingsResponse)
async def get_privacy_settings(request: Request):
    return await UserBusinessService(request=request).get_privacy_settings()


@router.patch("/settings/privacy", response_model=UserPrivacySettingsResponse)
async def update_privacy_settings(
    request: Request,
    dto: UserPrivacySettingsUpdateRequest,
):
    return await UserBusinessService(request=request).update_privacy_settings(dto=dto)
