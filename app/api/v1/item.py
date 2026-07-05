from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request

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
    request: Request,
    params: Annotated[ItemsCatalogQueryParams, Depends()],
):
    return await ItemsBusinessService(request=request).get_items(params=params)


@router.get("/my", response_model=MyItemsResponse)
async def get_my_items(
    request: Request,
    params: Annotated[ItemsCatalogQueryParams, Depends()],
):
    return await ItemsBusinessService(request=request).get_my_items(params=params)


@router.post("/secret", response_model=ValidationResponse)
async def collect_item_by_secret(
    request: Request,
    dto: SecretValidationRequest,
):
    return await ItemsBusinessService(request=request).collect_item_by_secret(dto=dto)


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    request: Request,
    item_id: Annotated[int, Path(gt=0)],
):
    return await ItemsBusinessService(request=request).get_item(item_id=item_id)


@router.get("/{item_id}/full", response_model=ItemFullResponse)
async def get_full_item(
    request: Request,
    item_id: Annotated[int, Path(gt=0)],
):
    return await ItemsBusinessService(request=request).get_full_item(item_id=item_id)


@router.get("/{item_id}/rating", response_model=ItemRatingResponse)
async def get_item_rating(
    request: Request,
    item_id: Annotated[int, Path(gt=0)],
    params: Annotated[ItemRatingQueryParams, Depends()],
):
    return await ItemsBusinessService(request=request).get_item_rating(
        item_id=item_id,
        params=params,
    )
