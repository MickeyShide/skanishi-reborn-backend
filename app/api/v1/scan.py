from fastapi import APIRouter, Request

from app.schemas.frontend import ScanClaimRequest, ScanClaimResponse
from app.services.business.frontend_data import FrontendDataBusinessService

router = APIRouter(prefix="/scan", tags=["Scan"])


@router.post("/claim", response_model=ScanClaimResponse)
async def claim_scan_reward(
    request: Request,
    dto: ScanClaimRequest,
):
    return await FrontendDataBusinessService(request=request).claim_scan_reward(dto=dto)
