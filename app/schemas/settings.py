from pydantic import BaseModel, Field


class MapApiKeyResponse(BaseModel):
    """Browser key for Yandex Maps runtime loading."""

    api_key: str = Field(
        min_length=1,
        description="Public browser API key for Yandex Maps v3",
    )


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
