from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.redis_client import redis_client, redis_fail_open
from app.schemas.profile import ValidationCountResponse
from app.services.business.base_authenticated import AuthenticatedBusinessService
from app.services.validation import ValidationService

VALIDATION_COUNT_CACHE_TTL_SECONDS = 600


class ProfileBusinessService(AuthenticatedBusinessService):
    validation_service: ValidationService

    def __init__(
        self,
        request: Request,
        session: AsyncSession | None = None,
    ) -> None:
        super().__init__(request=request, session=session)

    async def get_validation_count(self) -> ValidationCountResponse:
        user = await self.get_current_user()
        cache_key = f"user:{user.id}:validation_count"

        cached_count = await redis_fail_open(
            lambda: redis_client.get(cache_key),
            default=None,
        )
        parsed_cached_count = self._parse_cached_count(cached_count)

        if parsed_cached_count is not None:
            return ValidationCountResponse(count=parsed_cached_count)

        count = await self.validation_service.count_user_validations(user_id=user.id)

        await redis_fail_open(
            lambda: redis_client.set(
                name=cache_key,
                value=str(count),
                ex=VALIDATION_COUNT_CACHE_TTL_SECONDS,
            ),
            default=None,
        )

        return ValidationCountResponse(count=count)

    @staticmethod
    def _parse_cached_count(value: str | None) -> int | None:
        if value is None:
            return None

        try:
            parsed_value = int(value)
        except ValueError:
            return None

        return parsed_value if parsed_value >= 0 else None
