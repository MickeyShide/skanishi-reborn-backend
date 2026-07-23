from fastapi import APIRouter, Depends

from app.api.v1.dependencies import CurrentUser, enforce_csrf_protection
from app.schemas.shop import ShopItemResponse
from app.services.business.shop import ShopBusinessService

router = APIRouter(prefix="/shop", tags=["Shop"])

@router.get("", response_model=list[ShopItemResponse])
async def get_shop_items(
    current_user: CurrentUser,
) -> list[ShopItemResponse]:
    return await ShopBusinessService().get_shop_items(current_user)

@router.post(
    "/{item_id}/buy",
    response_model=ShopItemResponse,
    dependencies=[Depends(enforce_csrf_protection)],
)
async def buy_shop_item(
    item_id: int,
    current_user: CurrentUser,
) -> ShopItemResponse:
    return await ShopBusinessService().buy_item(current_user, item_id)

@router.post(
    "/{item_id}/equip",
    response_model=ShopItemResponse,
    dependencies=[Depends(enforce_csrf_protection)],
)
async def equip_shop_item(
    item_id: int,
    current_user: CurrentUser,
) -> ShopItemResponse:
    return await ShopBusinessService().equip_item(current_user, item_id)

@router.post(
    "/{item_id}/craft",
    response_model=ShopItemResponse,
    dependencies=[Depends(enforce_csrf_protection)],
)
async def craft_shop_item(
    item_id: int,
    current_user: CurrentUser,
) -> ShopItemResponse:
    return await ShopBusinessService().craft_item(current_user, item_id)
