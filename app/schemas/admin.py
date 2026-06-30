from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.common import Id


type Title = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=128,
        strip_whitespace=True,
    ),
]

type Description = Annotated[
    str,
    StringConstraints(
        max_length=4096,
    ),
]

type Color = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=32,
        strip_whitespace=True,
    ),
]

type Url = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=2048,
        strip_whitespace=True,
    ),
]


class CreateCategoryRequest(BaseModel):
    """Создание категории."""

    title: Title
    color: Color
    description: Description = ""


class UpdateCategoryRequest(BaseModel):
    """Обновление категории."""

    title: Title | None = None
    color: Color | None = None
    description: Description | None = None


class CreateTypeRequest(BaseModel):
    """Создание типа предмета."""

    title: Title
    description: Description = ""
    photo_url: Url | None = None


class UpdateTypeRequest(BaseModel):
    """Обновление типа предмета."""

    title: Title | None = None
    description: Description | None = None
    photo_url: Url | None = None


class CreatePrototypeRequest(BaseModel):
    """Создание прототипа предмета."""

    title: Title
    description: Description = ""
    photo_url: Url | None = None
    type_id: Id


class UpdatePrototypeRequest(BaseModel):
    """Обновление прототипа предмета."""

    title: Title | None = None
    description: Description | None = None
    photo_url: Url | None = None
    type_id: Id | None = None


class CreateItemRequest(BaseModel):
    """Создание цифрового предмета."""

    title: Title
    number: int = Field(
        gt=0,
        description="Глобальный номер предмета",
    )
    prototype_id: Id
    category_id: Id
    type_id: Id
    is_active: bool = True


class UpdateItemRequest(BaseModel):
    """Обновление цифрового предмета."""

    title: Title | None = None
    number: int | None = Field(
        default=None,
        gt=0,
        description="Глобальный номер предмета",
    )
    prototype_id: Id | None = None
    category_id: Id | None = None
    type_id: Id | None = None
    is_active: bool | None = None


class CreateItemSecretRequest(BaseModel):
    """Создание секрета предмета.

    Raw secret генерируется сервисом и не принимается от клиента.
    """

    title: Title
    coords: str | None = Field(
        default=None,
        max_length=128,
        description="Координаты или подсказка к месту QR",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Дата истечения секрета",
    )
    is_active: bool = True


class CreateSecretResponse(BaseModel):
    """Ответ создания секрета.

    Token возвращается только один раз.
    """

    id: Id
    item_id: Id
    token: str = Field(
        min_length=1,
        description="Одноразово возвращаемый QR/startapp token",
    )
    expires_at: datetime | None = None


class CreateItemImageRequest(BaseModel):
    """Добавление изображения предмета."""

    url: Url
    is_main: bool = False
    position: int = Field(
        default=0,
        ge=0,
        description="Позиция изображения в списке",
    )
