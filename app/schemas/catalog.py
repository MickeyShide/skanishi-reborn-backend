from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Id


class CategoryResponse(BaseModel):
    """Категория предметов."""

    id: Id = Field(
        description="Уникальный идентификатор категории",
    )
    title: str = Field(
        min_length=1,
        max_length=128,
        description="Название категории",
    )
    color: str = Field(
        min_length=1,
        max_length=32,
        description="Цвет категории: hex или design token",
    )
    description: str = Field(
        description="Описание категории",
    )


class TypeResponse(BaseModel):
    """Тип цифрового предмета."""

    id: Id = Field(
        description="Уникальный идентификатор типа",
    )
    title: str = Field(
        min_length=1,
        max_length=128,
        description="Название типа",
    )
    description: str = Field(
        description="Описание типа",
    )
    photo_url: str | None = Field(
        default=None,
        description="URL фотографии типа",
    )


class PrototypeResponse(BaseModel):
    """Прототип цифрового предмета."""

    id: Id = Field(
        description="Уникальный идентификатор прототипа",
    )
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
        description="Идентификатор типа цифрового предмета",
    )


class ItemImageResponse(BaseModel):
    """Изображение цифрового предмета."""

    id: Id
    item_id: Id
    url: str = Field(
        min_length=1,
        description="URL изображения",
    )
    is_main: bool = Field(
        default=False,
        description="Главное изображение предмета",
    )
    position: int = Field(
        default=0,
        ge=0,
        description="Позиция изображения в списке",
    )


class ItemBaseResponse(BaseModel):
    """Общая часть DTO цифрового предмета."""

    state: str = Field(
        description="Состояние цифрового предмета",
    )
    id: Id = Field(
        description="Уникальный идентификатор цифрового предмета",
    )
    title: str | None = Field(
        default=None,
        description="Название цифрового предмета",
    )
    number: int | None = Field(
        default=None,
        gt=0,
        description="Номер цифрового предмета",
    )
    type: TypeResponse = Field(
        description="Информация о типе цифрового предмета",
    )
    category: CategoryResponse = Field(
        description="Информация о категории цифрового предмета",
    )
    prototype: PrototypeResponse = Field(
        description="Информация о прототипе цифрового предмета",
    )


class ItemFullResponse(ItemBaseResponse):
    """Полное представление цифрового предмета."""

    state: Literal["collected"] = "collected"
    title: str = Field(
        min_length=1,
        max_length=128,
        description="Название цифрового предмета",
    )
    number: int = Field(
        gt=0,
        description="Номер цифрового предмета",
    )


class ItemHiddenResponse(ItemBaseResponse):
    """Скрытое представление цифрового предмета."""

    state: Literal["hidden"] = "hidden"
    title: None = Field(
        default=None,
        description="Скрыто до получения предмета",
    )
    number: None = Field(
        default=None,
        description="Скрыто до получения предмета",
    )


type ItemResponse = ItemFullResponse | ItemHiddenResponse
