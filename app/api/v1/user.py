from fastapi import APIRouter, Depends

from app.api.v1.dependencies import CurrentUser, enforce_csrf_protection

from app.schemas.user import (
    UserPrivacySettingsResponse,
    UserPrivacySettingsUpdateRequest,
)
from app.schemas.frontend import FrontendUserResponse
from app.services.business.user import UserBusinessService

router = APIRouter(prefix="/users", tags=["User"])


@router.get("/me", response_model=FrontendUserResponse, include_in_schema=False)
async def get_me(current_user: CurrentUser):
    return await UserBusinessService().get_me(current_user=current_user)


@router.get("/settings/privacy", response_model=UserPrivacySettingsResponse)
async def get_privacy_settings(current_user: CurrentUser):
    return await UserBusinessService().get_privacy_settings(current_user=current_user)


@router.patch(
    "/settings/privacy",
    response_model=UserPrivacySettingsResponse,
    dependencies=[Depends(enforce_csrf_protection)],
)
async def update_privacy_settings(
    current_user: CurrentUser,
    dto: UserPrivacySettingsUpdateRequest,
):
    return await UserBusinessService().update_privacy_settings(current_user=current_user, dto=dto)
