import asyncio
from unittest.mock import MagicMock, AsyncMock

async def main():
    service = MagicMock()
    service.get_active_by_secret_hash = AsyncMock()
    hashed_secret = service.hash_secret("raw_secret")
    print("hash_secret type:", type(hashed_secret))
    item_secret = await service.get_active_by_secret_hash(hashed_secret)
    print("item_secret:", item_secret)

asyncio.run(main())
