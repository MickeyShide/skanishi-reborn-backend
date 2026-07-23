from __future__ import annotations

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from app.api.v1 import ugc
from app.services.errors import StickerAlreadyExistsError, StickerNotFoundError


class UgcApiTests(IsolatedAsyncioTestCase):
    async def test_get_my_sticker_uses_business_service(self) -> None:
        sticker = SimpleNamespace(
            token="ugc_token",
            scan_count=3,
            total_passive_xp=15,
            total_passive_coins=7,
        )
        service = AsyncMock()
        service.get_my_sticker.return_value = sticker

        response = await ugc.get_my_sticker(
            current_user=SimpleNamespace(id=1),
            service=service,
        )

        service.get_my_sticker.assert_awaited_once_with(
            current_user=SimpleNamespace(id=1),
        )
        self.assertEqual(response.secret, "ugc_token")

    async def test_get_my_sticker_maps_not_found_error(self) -> None:
        service = AsyncMock()
        service.get_my_sticker.side_effect = StickerNotFoundError()

        with self.assertRaises(StickerNotFoundError) as exc_info:
            await ugc.get_my_sticker(
                current_user=SimpleNamespace(id=1),
                service=service,
            )

        self.assertEqual(exc_info.exception.status_code, 404)

    async def test_generate_my_sticker_uses_business_service(self) -> None:
        sticker = SimpleNamespace(
            token="ugc_generated",
            scan_count=0,
            total_passive_xp=0,
            total_passive_coins=0,
        )
        service = AsyncMock()
        service.generate_my_sticker.return_value = sticker

        response = await ugc.generate_my_sticker(
            current_user=SimpleNamespace(id=1),
            service=service,
        )

        service.generate_my_sticker.assert_awaited_once()
        self.assertEqual(response.secret, "ugc_generated")

    async def test_generate_my_sticker_maps_duplicate_error(self) -> None:
        service = AsyncMock()
        service.generate_my_sticker.side_effect = StickerAlreadyExistsError()

        with self.assertRaises(StickerAlreadyExistsError) as exc_info:
            await ugc.generate_my_sticker(
                current_user=SimpleNamespace(id=1),
                service=service,
            )

        self.assertEqual(exc_info.exception.status_code, 400)
