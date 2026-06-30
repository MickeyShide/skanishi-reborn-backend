from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router

routers = [health_router, auth_router]
