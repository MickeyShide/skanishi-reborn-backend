from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import CurrentUser, enforce_csrf_protection
from app.services.business.collections import (
    CollectionBusinessService,
    CollectionClaimResponse,
    CollectionResponse,
)

router = APIRouter(prefix="/collections", tags=["Collections"])


@router.get("", response_model=list[CollectionResponse])
async def get_collections(current_user: CurrentUser) -> list[CollectionResponse]:
    """Return all active collections and the current user's progress."""
    return await CollectionBusinessService().get_user_collections(current_user)


@router.post(
    "/{collection_id}/claim",
    response_model=CollectionClaimResponse,
    dependencies=[Depends(enforce_csrf_protection)],
)
async def claim_collection_reward(
    collection_id: str,
    current_user: CurrentUser,
) -> CollectionClaimResponse:
    """Claim the XP reward for a completed collection."""
    return await CollectionBusinessService().claim_reward(current_user, collection_id)
