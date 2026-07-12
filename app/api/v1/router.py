from fastapi import APIRouter

from app.api.v1.achievement import router as achievement_router
from app.api.v1.app_state import router as app_state_router
from app.api.v1.auth import router as auth_router
from app.api.v1.collection import router as collection_router
from app.api.v1.daily import router as daily_router
from app.api.v1.events import router as events_router
from app.api.v1.health import router as health_router
from app.api.v1.item import router as item_router
from app.api.v1.leaderboard import router as leaderboard_router
from app.api.v1.map import router as map_router
from app.api.v1.profile import router as profile_router
from app.api.v1.quest import router as quest_router
from app.api.v1.referral import router as referral_router
from app.api.v1.scan import router as scan_router
from app.api.v1.shop import router as shop_router
from app.api.v1.stream import router as stream_router
from app.api.v1.user import router as user_router
from app.api.v1.ugc import router as ugc_router
from app.api.v1.xp import router as xp_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(health_router)
v1_router.include_router(auth_router)
v1_router.include_router(item_router)
v1_router.include_router(collection_router)
v1_router.include_router(events_router)
v1_router.include_router(profile_router)
v1_router.include_router(user_router)
v1_router.include_router(app_state_router)
v1_router.include_router(map_router)
v1_router.include_router(quest_router)
v1_router.include_router(daily_router)
v1_router.include_router(xp_router)
v1_router.include_router(achievement_router)
v1_router.include_router(leaderboard_router)
v1_router.include_router(referral_router)
v1_router.include_router(scan_router)
v1_router.include_router(shop_router)
v1_router.include_router(ugc_router)
v1_router.include_router(stream_router)
