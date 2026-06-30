from pydantic import BaseModel, Field


class PrivacyResponse(BaseModel):
    """Текущая настройка приватности пользователя."""

    privacy: bool = Field(
        description="true, если профиль скрыт в рейтингах",
    )


class PrivacyUpdateRequest(BaseModel):
    """Запрос на изменение приватности пользователя."""

    privacy: bool = Field(
        description="Новое значение приватности",
    )
