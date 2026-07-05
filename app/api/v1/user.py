from fastapi import APIRouter

from app.api.v1.dependencies import CurrentUser

from app.schemas.user import (
    UserPrivacySettingsResponse,
    UserPrivacySettingsUpdateRequest,
)
from app.services.business.user import UserBusinessService

router = APIRouter(prefix="/users", tags=["User"])


@router.get("/settings/privacy", response_model=UserPrivacySettingsResponse)
async def get_privacy_settings(current_user: CurrentUser):
    return await UserBusinessService().get_privacy_settings(current_user=current_user)


@router.patch("/settings/privacy", response_model=UserPrivacySettingsResponse)
async def update_privacy_settings(
    current_user: CurrentUser,
    dto: UserPrivacySettingsUpdateRequest,
):
    return await UserBusinessService().update_privacy_settings(current_user=current_user, dto=dto)
