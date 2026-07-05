from app.api.v1.achievement import router as achievement_router
from app.api.v1.app_state import router as app_state_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.item import router as item_router
from app.api.v1.map import router as map_router
from app.api.v1.profile import router as profile_router
from app.api.v1.quest import router as quest_router
from app.api.v1.scan import router as scan_router
from app.api.v1.user import router as user_router
from app.api.v1.xp import router as xp_router

routers = [
    health_router,
    auth_router,
    item_router,
    profile_router,
    user_router,
    app_state_router,
    map_router,
    quest_router,
    xp_router,
    achievement_router,
    scan_router,
]
