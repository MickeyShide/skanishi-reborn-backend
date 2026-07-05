from fastapi import APIRouter, Request

from app.schemas.profile import ValidationCountResponse
from app.services.business.profile import ProfileBusinessService

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/validations/count", response_model=ValidationCountResponse)
async def get_validation_count(request: Request):
    return await ProfileBusinessService(request=request).get_validation_count()
