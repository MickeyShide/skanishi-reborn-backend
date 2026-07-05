from pydantic import BaseModel, ConfigDict, Field

from app.db.models.user import UserRole


class UserPublic(BaseModel):
    """Публичное представление пользователя."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        gt=0,
        description="Уникальный идентификатор пользователя",
    )
    first_name: str = Field(
        min_length=1,
        max_length=128,
        description="Имя пользователя",
    )
    last_name: str | None = Field(
        default=None,
        max_length=128,
        description="Фамилия пользователя",
    )
    photo_url: str | None = Field(
        default=None,
        description="URL фотографии пользователя",
    )
    is_private: bool = Field(
        default=False,
        description="Флаг приватности профиля",
    )


class UserMe(UserPublic):
    """Информация о текущем пользователе."""

    tg_id: int = Field(
        gt=0,
        description="Telegram ID пользователя",
    )
    username: str | None = Field(
        default=None,
        max_length=64,
        description="Имя пользователя в Telegram",
    )
    is_premium: bool = Field(
        default=False,
        description="Флаг Telegram Premium",
    )
    role: UserRole = Field(
        description="Роль пользователя в системе",
    )


class UserPrivacySettingsResponse(BaseModel):
    """Настройки приватности текущего пользователя."""

    privacy: bool = Field(
        description="Флаг приватности профиля текущего пользователя",
    )


class UserPrivacySettingsUpdateRequest(BaseModel):
    """Запрос на обновление настройки приватности."""

    privacy: bool = Field(
        description="Новое значение приватности профиля",
    )
