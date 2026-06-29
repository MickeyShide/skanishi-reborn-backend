from collections.abc import Awaitable, Callable

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings
from app.core.logger import logger

redis_client: Redis = Redis.from_url(
    settings.REDIS_URL.unicode_string(),
    decode_responses=True,
)


async def check_redis() -> None:
    await redis_client.ping()


async def close_redis() -> None:
    await redis_client.aclose()


async def redis_fail_open[T](
    operation: Callable[[], Awaitable[T]],
    default: T | None = None,
) -> T | None:
    try:
        return await operation()
    except RedisError:
        logger.warning(
            "Redis operation failed; continuing in fail-open mode",
            exc_info=True,
        )
        return default
