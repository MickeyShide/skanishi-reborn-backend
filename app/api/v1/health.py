from fastapi import APIRouter, HTTPException, status

from app.core.database import check_database
from app.core.redis_client import check_redis

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
async def live_health():
    return {"status": "ok"}


@router.get("/ready")
async def ready_health():
    checks: dict[str, str] = {}
    errors: dict[str, str] = {}

    try:
        await check_database()
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = "error"
        errors["database"] = str(exc)

    try:
        await check_redis()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = "error"
        errors["redis"] = str(exc)

    if errors:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Readiness check failed.",
                "checks": checks,
                "errors": errors,
            },
        )

    return {"status": "ok", "checks": checks}
