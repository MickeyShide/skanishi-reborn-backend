from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.v1.dependencies import CurrentUser

from app.schemas.common import ItemRatingQueryParams, ItemsCatalogQueryParams
from app.schemas.item import (
    ItemFullResponse,
    ItemResponse,
    ItemsResponse,
    MyItemsResponse,
)
from app.schemas.validation import (
    ItemRatingResponse,
    SecretValidationRequest,
    ValidationResponse,
)
from app.services.business.items import ItemsBusinessService

router = APIRouter(prefix="/items", tags=["Item"])


@router.get("", response_model=ItemsResponse)
async def get_items(
    current_user: CurrentUser,
    params: Annotated[ItemsCatalogQueryParams, Depends()],
):
    return await ItemsBusinessService().get_items(current_user=current_user, params=params)


@router.get("/my", response_model=MyItemsResponse)
async def get_my_items(
    current_user: CurrentUser,
    params: Annotated[ItemsCatalogQueryParams, Depends()],
):
    return await ItemsBusinessService().get_my_items(current_user=current_user, params=params)


from app.api.v1.dependencies import CurrentUser, enforce_csrf_protection

@router.post(
    "/secret",
    response_model=ValidationResponse,
    dependencies=[Depends(enforce_csrf_protection)],
)
async def collect_item_by_secret(
    current_user: CurrentUser,
    dto: SecretValidationRequest,
):
    return await ItemsBusinessService().collect_item_by_secret(current_user=current_user, dto=dto)


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    current_user: CurrentUser,
    item_id: Annotated[int, Path(gt=0)],
):
    return await ItemsBusinessService().get_item(current_user=current_user, item_id=item_id)


@router.get("/{item_id}/full", response_model=ItemFullResponse)
async def get_full_item(
    current_user: CurrentUser,
    item_id: Annotated[int, Path(gt=0)],
):
    return await ItemsBusinessService().get_full_item(current_user=current_user, item_id=item_id)


@router.get("/{item_id}/rating", response_model=ItemRatingResponse)
async def get_item_rating(
    current_user: CurrentUser,
    item_id: Annotated[int, Path(gt=0)],
    params: Annotated[ItemRatingQueryParams, Depends()],
):
    return await ItemsBusinessService().get_item_rating(
        current_user=current_user,
        item_id=item_id,
        params=params,
    )
