import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.v1.dependencies import CurrentUser
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
    try:
        sticker = await service.get_my_sticker(current_user=current_user)
    except ValueError as exc:
        if str(exc) != "sticker_not_found":
            raise
        raise HTTPException(status_code=404, detail="Стикер не найден") from exc

    return _to_response(sticker)


@router.post("/generate", response_model=UgcStickerResponse)
async def generate_my_sticker(
    current_user: CurrentUser,
    service: Annotated[UGCBusinessService, Depends(get_ugc_business_service)],
) -> UgcStickerResponse:
    try:
        sticker = await service.generate_my_sticker(
            current_user=current_user,
            token_factory=lambda: f"ugc_{uuid.uuid4().hex}",
        )
    except ValueError as exc:
        if str(exc) != "sticker_already_exists":
            raise
        raise HTTPException(
            status_code=400,
            detail="Стикер уже сгенерирован",
        ) from exc

    return _to_response(sticker)
