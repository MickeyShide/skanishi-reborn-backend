from fastapi import APIRouter

from app.core.database import check_database
from app.core.redis_client import check_redis
from app.services.errors import ServiceNotReadyError

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
async def live_health():
    return {"status": "ok"}


@router.get("/ready")
async def ready_health():
    details = {
        "db": "ok",
        "redis": "ok",
    }

    try:
        await check_database()
    except Exception:
        details["db"] = "failed"

    try:
        await check_redis()
    except Exception:
        details["redis"] = "failed"

    if details["db"] != "ok" or details["redis"] != "ok":
        raise ServiceNotReadyError(details=details)

    return {"status": "ready", **details}
