# app/services/init_data_replay_guard.py

from __future__ import annotations

import hashlib

from redis.asyncio import Redis

from app.services.errors import InitDataReplayError


class InitDataReplayGuardService:
    def __init__(self, redis: Redis, *, ttl_seconds: int = 3600) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    async def ensure_not_replayed(self, init_data: str) -> None:
        init_data_hash = hashlib.sha256(init_data.encode()).hexdigest()
        key = f"tg_init_data:{init_data_hash}"

        was_set = await self.redis.set(
            name=key,
            value="1",
            ex=self.ttl_seconds,
            nx=True,
        )

        if not was_set:
            raise InitDataReplayError()
