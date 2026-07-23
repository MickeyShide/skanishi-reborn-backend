from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.user import UserMe

type TelegramInitData = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=4096,
        strip_whitespace=True,
    ),
]


class TelegramAuthRequest(BaseModel):
    """Входные данные для авторизации через Telegram.

    Для endpoint из ТЗ поле приходит как form field `tg_web_app_data`.
    """

    tg_web_app_data: TelegramInitData = Field(
        description="Строка window.Telegram.WebApp.initData",
    )


class TokenResponse(BaseModel):
    """Ответ с access-token и информацией о пользователе.

    Refresh-token в JSON не возвращается. Он устанавливается только в HttpOnly cookie.
    """

    access_token: str = Field(
        min_length=1,
        description="JWT access-token",
    )
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int = Field(
        gt=0,
        description="Время жизни access-token в секундах",
    )
    user: UserMe


class AccessTokenClaims(BaseModel):
    """Claims access-token."""

    sub: str
    id: int
    tg_id: int
    role: str
    token_type: Literal["access"]
    iat: int
    exp: int


class RefreshTokenClaims(BaseModel):
    """Claims refresh-token."""

    sub: str
    id: int
    jti: str
    token_type: Literal["refresh"]
    iat: int
    exp: int
