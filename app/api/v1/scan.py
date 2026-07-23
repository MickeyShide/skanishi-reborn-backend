from fastapi import APIRouter

from app.api.v1.dependencies import CurrentUser
from app.schemas.frontend import ScanClaimRequest, ScanClaimResponse
from app.services.business.frontend_data import FrontendDataBusinessService

router = APIRouter(prefix="/scan", tags=["Scan"])


from app.api.v1.dependencies import enforce_csrf_protection
from fastapi import Depends

@router.post(
    "/claim",
    response_model=ScanClaimResponse,
    dependencies=[Depends(enforce_csrf_protection)],
)
async def claim_scan_reward(
    current_user: CurrentUser,
    dto: ScanClaimRequest,
):
    return await FrontendDataBusinessService().claim_scan_reward(
        current_user=current_user,
        dto=dto,
    )
