from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Id, PaginatedResponse
from app.schemas.item_type import ItemTypeResponse


class CategoryResponse(BaseModel):
    """Категория предмета."""

    model_config = ConfigDict(from_attributes=True)

    id: Id
    title: str = Field(
        min_length=1,
        max_length=128,
        description="Название категории",
    )
    color: str = Field(
        min_length=1,
        max_length=32,
        description="HEX-цвет или design token категории",
    )
    description: str = Field(
        description="Описание категории",
    )


class PrototypeResponse(BaseModel):
    """Прототип предмета."""

    model_config = ConfigDict(from_attributes=True)

    id: Id
    title: str = Field(
        min_length=1,
        max_length=128,
        description="Название прототипа",
    )
    description: str = Field(
        description="Описание прототипа",
    )
    photo_url: str | None = Field(
        default=None,
        description="URL фотографии прототипа",
    )
    type_id: Id = Field(
        description="Идентификатор типа предмета",
    )


class ItemBaseResponse(BaseModel):
    """Базовая схема ответа для предмета."""

    id: Id
    state: Literal["collected", "hidden"] = Field(
        description="Состояние видимости предмета для пользователя",
    )
    title: str | None = Field(
        default=None,
        description="Название предмета или null для скрытого вида",
    )
    number: int | None = Field(
        default=None,
        gt=0,
        description="Порядковый номер предмета или null для скрытого вида",
    )
    type: ItemTypeResponse
    category: CategoryResponse
    prototype: PrototypeResponse


class ItemFullResponse(ItemBaseResponse):
    """Полное представление предмета."""

    state: Literal["collected"] = "collected"
    title: str = Field(
        min_length=1,
        max_length=128,
        description="Название предмета",
    )
    number: int = Field(
        gt=0,
        description="Порядковый номер предмета",
    )


class ItemHiddenResponse(ItemBaseResponse):
    """Скрытое представление несобранного предмета."""

    state: Literal["hidden"] = "hidden"
    title: None = Field(
        default=None,
        description="Название скрыто до получения предмета",
    )
    number: None = Field(
        default=None,
        description="Номер скрыт до получения предмета",
    )


type ItemResponse = ItemFullResponse | ItemHiddenResponse


class ItemsResponse(PaginatedResponse[ItemFullResponse]):
    """Каталог предметов в полном виде."""


class MyItemsResponse(PaginatedResponse[ItemResponse]):
    """Каталог предметов с учетом коллекции пользователя."""

