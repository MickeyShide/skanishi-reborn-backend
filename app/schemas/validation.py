from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.common import Id, PaginatedResponse
from app.schemas.item import ItemFullResponse
from app.schemas.user import UserPublic

type SecretToken = Annotated[
    str,
    StringConstraints(
        min_length=16,
        max_length=4096,
        strip_whitespace=True,
        pattern=r"^[A-Za-z0-9_\-.]+$",
    ),
]


class SecretValidationRequest(BaseModel):
    """Запрос на обработку QR/startapp secret token."""

    token: SecretToken = Field(
        description="base64url/JWT token с item secret",
    )


class ItemSecretTokenClaims(BaseModel):
    """Claims QR/startapp токена предмета."""

    secret: str = Field(
        min_length=1,
        description="Сырой secret из токена. В БД не хранится.",
    )
    token_type: Literal["item_secret"]
    iat: int
    exp: int


class ValidationShortResponse(BaseModel):
    """Краткая информация о факте получения предмета."""

    id: Id
    item_id: Id
    rank: int = Field(
        gt=0,
        description="Порядковый номер получения конкретного item",
    )
    created_at: datetime = Field(
        description="Дата создания validation в ISO 8601 UTC",
    )


class ValidationResponse(BaseModel):
    """Ответ после обработки QR/startapp token."""

    status: Literal["created", "already_collected"]
    validation: ValidationShortResponse
    item: ItemFullResponse


class RatingEntryResponse(BaseModel):
    """Строка рейтинга по конкретному item."""

    rank: int = Field(
        gt=0,
        description="Позиция пользователя в рейтинге item",
    )
    created_at: datetime = Field(
        description="Дата получения item в ISO 8601 UTC",
    )
    user: UserPublic | None = Field(
        default=None,
        description="Публичный пользователь или null, если профиль приватный",
    )


class ItemRatingResponse(PaginatedResponse[RatingEntryResponse]):
    """Пагинированный рейтинг по предмету."""
