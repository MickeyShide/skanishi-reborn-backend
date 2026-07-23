from fastapi import APIRouter

from app.api.v1.dependencies import CurrentUser
from app.schemas.frontend import ProfileResponse
from app.schemas.profile import ValidationCountResponse
from app.services.business.profile import ProfileBusinessService

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/validations/count", response_model=ValidationCountResponse)
async def get_validation_count(current_user: CurrentUser):
    return await ProfileBusinessService().get_validation_count(current_user=current_user)


@router.get("", response_model=ProfileResponse, include_in_schema=False)
async def get_profile(current_user: CurrentUser):
    return await ProfileBusinessService().get_profile(current_user=current_user)
