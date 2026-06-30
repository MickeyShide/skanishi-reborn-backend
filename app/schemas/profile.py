from pydantic import BaseModel, Field


class ValidationCountResponse(BaseModel):
    """Количество собранных предметов текущим пользователем."""

    count: int = Field(
        ge=0,
        description="Количество validation текущего пользователя",
    )
