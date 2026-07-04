from __future__ import annotations

from hmac import compare_digest
from typing import Annotated

from fastapi import Depends, Request

from app.core.database import session_context
from app.db.models.user import User
from app.db.repositories.errors import ObjectNotFoundError
from app.services.business.auth import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    csrf_protection_enabled,
    get_bearer_token,
)
from app.services.errors import ForbiddenError, InvalidAccessTokenError, UserNotFoundError
from app.services.token import TokenService
from app.services.user import UserService


async def enforce_csrf_protection(request: Request) -> None:
    if not csrf_protection_enabled():
        return

    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(CSRF_HEADER_NAME)

    if not csrf_cookie or not csrf_header:
        raise ForbiddenError("CSRF validation failed.")

    if not compare_digest(csrf_cookie, csrf_header):
        raise ForbiddenError("CSRF validation failed.")


async def get_current_user(request: Request) -> User:
    access_token = get_bearer_token(request)
    claims = TokenService().decode_access_token(access_token)

    try:
        user_id = int(claims.sub)
    except ValueError as exc:
        raise InvalidAccessTokenError from exc

    async with session_context() as session:
        user_service = UserService(session)
        try:
            return await user_service.get_user_by_id(user_id)
        except ObjectNotFoundError as exc:
            raise UserNotFoundError from exc


CurrentUser = Annotated[User, Depends(get_current_user)]
