from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from app.config import settings


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        # Use the configured admin secret key
        # In a real app, this should be checked securely
        expected_secret = settings.ADMIN_SECRET_KEY or "admin"
        
        if username == "admin" and password == expected_secret:
            request.session.update({"token": "admin_token"})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        return True

authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
