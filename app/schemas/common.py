from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


type Id = Annotated[
    int,
    Field(
        gt=0,
        description="Положительный идентификатор сущности",
    ),
]

type Limit = Annotated[
    int,
    Field(
        ge=1,
        le=100,
        description="Количество элементов на странице",
    ),
]

type CatalogLimit = Annotated[
    int,
    Field(
        ge=1,
        le=200,
        description="Количество элементов каталога на странице",
    ),
]

type Offset = Annotated[
    int,
    Field(
        ge=0,
        description="Смещение от начала",
    ),
]

type Total = Annotated[
    int,
    Field(
        ge=0,
        description="Общее количество элементов",
    ),
]


class PaginatedQueryParams(BaseModel):
    """Параметры для запросов с пагинацией limit/offset."""

    limit: Limit = 20
    offset: Offset = 0


class CatalogQueryParams(BaseModel):
    """Параметры запроса каталога."""

    limit: CatalogLimit = 100
    offset: Offset = 0
    category_id: Id | None = Field(
        default=None,
        description="Фильтр по категории",
    )
    type_id: Id | None = Field(
        default=None,
        description="Фильтр по типу предмета",
    )


class PageMeta(BaseModel):
    """Метаданные страницы."""

    limit: int = Field(
        ge=1,
        description="Количество элементов на странице",
    )
    offset: Offset
    total: Total


class PaginatedResponse[T](BaseModel):
    """Универсальный ответ для списков с пагинацией."""

    items: list[T]
    meta: PageMeta


class ErrorDetail(BaseModel):
    """Детали ошибки API."""

    code: str = Field(
        description="Внутренний строковый код ошибки для фронтенда",
    )
    message: str = Field(
        description="Человекочитаемое описание ошибки",
    )
    details: Any | None = Field(
        default=None,
        description="Дополнительная детализация, например ошибки валидации",
    )
    request_id: str | None = Field(
        default=None,
        description="Уникальный ID запроса для техподдержки",
    )


class ErrorResponse(BaseModel):
    """Стандартный ответ API при ошибке."""

    error: ErrorDetail


class HealthLiveResponse(BaseModel):
    """Ответ live healthcheck."""

    status: Literal["ok"] = "ok"


class HealthReadyResponse(BaseModel):
    """Ответ readiness healthcheck."""

    status: Literal["ready"] = "ready"
    db: Literal["ok"]
    redis: Literal["ok"]


class EmptyResponse(BaseModel):
    """Пустой объектный ответ, если нужен JSON вместо 204."""

    pass
