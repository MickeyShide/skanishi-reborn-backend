from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(description="Внутренний строковый код ошибки для фронтенда")
    message: str = Field(description="Человекочитаемое описание ошибки")
    details: Any | None = Field(
        default=None,
        description="Дополнительная детализация (например, ошибки валидации)",
    )
    request_id: str | None = Field(
        default=None, description="Уникальный ID запроса для техподдержки"
    )


class ErrorResponse(BaseModel):
    error: ErrorDetail
