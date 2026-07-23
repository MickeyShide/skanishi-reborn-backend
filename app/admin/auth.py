import secrets

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.config import settings


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        expected_secret = settings.ADMIN_SECRET_KEY

        if (
            expected_secret
            and username == "admin"
            and secrets.compare_digest(password or "", expected_secret)
        ):
            request.session.update({"authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("authenticated"))


authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
