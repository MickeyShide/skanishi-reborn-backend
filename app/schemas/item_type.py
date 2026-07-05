from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Id


class ItemTypeResponse(BaseModel):
    """Схема ответа для типа предмета."""

    model_config = ConfigDict(from_attributes=True)

    id: Id
    title: str = Field(
        min_length=1,
        max_length=128,
        description="Название типа предмета",
    )
    description: str = Field(
        description="Описание типа предмета",
    )
    photo_url: str | None = Field(
        default=None,
        description="URL фотографии типа предмета",
    )

