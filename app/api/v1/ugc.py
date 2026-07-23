import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.v1.dependencies import CurrentUser, enforce_csrf_protection
from app.services.business.ugc import UGCBusinessService

router = APIRouter(prefix="/ugc", tags=["UGC"])


class UgcStickerResponse(BaseModel):
    secret: str
    scan_count: int
    total_passive_xp: int
    total_passive_coins: int


def _to_response(sticker: object) -> UgcStickerResponse:
    return UgcStickerResponse(
        secret=sticker.token,
        scan_count=sticker.scan_count,
        total_passive_xp=sticker.total_passive_xp,
        total_passive_coins=sticker.total_passive_coins,
    )


def get_ugc_business_service() -> UGCBusinessService:
    return UGCBusinessService()


@router.get("/me", response_model=UgcStickerResponse)
async def get_my_sticker(
    current_user: CurrentUser,
    service: Annotated[UGCBusinessService, Depends(get_ugc_business_service)],
) -> UgcStickerResponse:
    return _to_response(await service.get_my_sticker(current_user=current_user))


@router.post(
    "/generate",
    response_model=UgcStickerResponse,
    dependencies=[Depends(enforce_csrf_protection)],
)
async def generate_my_sticker(
    current_user: CurrentUser,
    service: Annotated[UGCBusinessService, Depends(get_ugc_business_service)],
) -> UgcStickerResponse:
    sticker = await service.generate_my_sticker(
        current_user=current_user,
        token_factory=lambda: f"ugc_{uuid.uuid4().hex}",
    )
    return _to_response(sticker)
