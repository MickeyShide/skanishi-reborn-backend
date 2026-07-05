from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.item import router as item_router

routers = [health_router, auth_router, item_router]
