import base64
import time
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import jwt

from app.config import settings
from app.db.models.user import UserRole
from app.schemas.common import ItemRatingQueryParams, ItemsCatalogQueryParams
from app.schemas.validation import ItemSecretTokenClaims, SecretValidationRequest
from app.services.business.items import ItemsBusinessService
from app.services.errors import (
    InvalidSecretTypeError,
    ItemNotCollectedError,
    MissingSecretError,
)


def build_catalog_row(
    item_id: int = 1,
    *,
    title: str = "Known item",
    number: int = 7,
) -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace, SimpleNamespace]:
    item = SimpleNamespace(
        id=item_id,
        title=title,
        number=number,
        category_id=11,
        prototype_id=12,
        type_id=10,
        validation_count=3,
    )
    category = SimpleNamespace(
        id=11,
        title="Museum",
        color="#112233",
        description="Museum items",
    )
    prototype = SimpleNamespace(
        id=12,
        title="Prototype",
        description="Prototype description",
        photo_url="https://example.com/prototype.png",
        type_id=10,
    )
    item_type = SimpleNamespace(
        id=10,
        title="Artifact",
        description="Rare type",
        photo_url="https://example.com/type.png",
    )
    return item, category, prototype, item_type


class ItemsBusinessServiceScenarioTests(IsolatedAsyncioTestCase):
    async def test_get_my_items_marks_hidden_and_collected_entries(self) -> None:
        service = object.__new__(ItemsBusinessService)
        service.get_current_user = AsyncMock(return_value=SimpleNamespace(id=77))
        service.item_service = MagicMock()
        service.item_service.get_active_catalog_page = AsyncMock(
            return_value=[
                build_catalog_row(item_id=1, title="Hidden item", number=1),
                build_catalog_row(item_id=2, title="Known item", number=2),
            ]
        )
        service.item_service.count_active_catalog = AsyncMock(return_value=2)
        service.validation_service = MagicMock()
        service.validation_service.get_user_item_ids = AsyncMock(return_value={2})

        user = await service.get_current_user()
        result = await ItemsBusinessService.get_my_items(
            service,
            user,
            ItemsCatalogQueryParams(),
        )

        self.assertEqual(result.meta.total, 2)
        self.assertEqual(result.items[0].state, "hidden")
        self.assertIsNone(result.items[0].title)
        self.assertEqual(result.items[1].state, "collected")
        self.assertEqual(result.items[1].title, "Known item")

    async def test_get_full_item_requires_collection_for_regular_user(self) -> None:
        service = object.__new__(ItemsBusinessService)
        service.get_current_user = AsyncMock(
            return_value=SimpleNamespace(id=77, role=UserRole.USER)
        )
        service._get_catalog_item_or_raise = AsyncMock(return_value=build_catalog_row())
        service.validation_service = MagicMock()
        service.validation_service.get_user_item_validation = AsyncMock(
            return_value=None
        )

        with self.assertRaises(ItemNotCollectedError):
            user = await service.get_current_user()
            await ItemsBusinessService.get_full_item(service, user, 1)

    async def test_get_full_item_allows_admin_without_validation(self) -> None:
        service = object.__new__(ItemsBusinessService)
        service.get_current_user = AsyncMock(
            return_value=SimpleNamespace(id=77, role=UserRole.ADMIN)
        )
        service._get_catalog_item_or_raise = AsyncMock(return_value=build_catalog_row())
        service.validation_service = MagicMock()
        service.validation_service.get_user_item_validation = AsyncMock()

        user = await service.get_current_user()
        result = await ItemsBusinessService.get_full_item(service, user, 1)

        self.assertEqual(result.state, "collected")
        self.assertEqual(result.title, "Known item")
        self.assertEqual(
            service.validation_service.get_user_item_validation.await_count,
            0,
        )

    async def test_get_item_rating_hides_private_users(self) -> None:
        service = object.__new__(ItemsBusinessService)
        service.get_current_user = AsyncMock(return_value=SimpleNamespace(id=77))
        service.item_service = MagicMock()
        service.item_service.get_active_item_by_id = AsyncMock(
            return_value=SimpleNamespace(id=1)
        )
        validation = SimpleNamespace(
            rank=1,
            created_at="2026-06-29T06:00:00Z",
        )
        private_user = SimpleNamespace(is_private=True)
        service.validation_service = MagicMock()
        service.validation_service.get_item_rating_page = AsyncMock(
            return_value=[(validation, private_user)]
        )
        service.validation_service.count_item_rating = AsyncMock(return_value=1)

        user = await service.get_current_user()
        result = await ItemsBusinessService.get_item_rating(
            service,
            user,
            1,
            ItemRatingQueryParams(),
        )

        self.assertIsNone(result.items[0].user)

    async def test_collect_item_by_secret_creates_validation_and_invalidates_cache(
        self,
    ) -> None:
        token = "abc.def.ghijklmnop"
        service = object.__new__(ItemsBusinessService)
        service.get_access_claims = MagicMock(return_value=SimpleNamespace(sub="77"))
        service._decode_item_secret_token = MagicMock(
            return_value=ItemSecretTokenClaims(
                secret="raw-secret",
                token_type="item_secret",
                iat=1710000000,
                exp=1810000000,
            )
        )

        item_service = MagicMock()
        item_service.get_active_catalog_item = AsyncMock(
            return_value=build_catalog_row()
        )
        item_service.get_active_item_for_update = AsyncMock(
            return_value=build_catalog_row()[0]
        )
        item_service.increment_validation_count = AsyncMock()

        validation = SimpleNamespace(
            id=9,
            item_id=1,
            rank=4,
            created_at="2026-06-29T06:00:00Z",
        )
        validation_service = MagicMock()
        validation_service.get_user_item_validation = AsyncMock(return_value=None)
        validation_service.create_validation = AsyncMock(return_value=validation)

        item_secret_service = MagicMock()
        item_secret_service.hash_secret.return_value = "secret-hash"
        item_secret_service.get_active_by_secret_hash = AsyncMock(
            return_value=SimpleNamespace(id=5, item_id=1)
        )

        service.item_service = item_service
        service.validation_service = validation_service
        service.item_secret_service = item_secret_service
        with (
            patch("app.services.business.items.ItemService", return_value=item_service),
            patch(
                "app.services.business.items.ValidationService",
                return_value=validation_service,
            ),
            patch(
                "app.services.business.items.ItemSecretService",
                return_value=item_secret_service,
            ),
            patch("app.services.business.items.UserService", return_value=user_service),
            patch("app.services.business.items.redis_fail_open", new_callable=AsyncMock) as redis_fail_open_mock,
        ):
            result = await ItemsBusinessService.collect_item_by_secret(
                service,
                SimpleNamespace(id=77),
                SecretValidationRequest(token=token),
            )

        self.assertEqual(result.status, "created")
        self.assertEqual(result.validation.rank, 4)
        item_service.increment_validation_count.assert_awaited_once()
        validation_service.create_validation.assert_awaited_once_with(
            user_id=77,
            item_id=1,
            item_secret_id=5,
            rank=4,
        )
        redis_fail_open_mock.assert_awaited_once()

    async def test_collect_item_by_secret_returns_existing_validation(self) -> None:
        token = "abc.def.ghijklmnop"
        service = object.__new__(ItemsBusinessService)
        service.get_access_claims = MagicMock(return_value=SimpleNamespace(sub="77"))
        service._decode_item_secret_token = MagicMock(
            return_value=ItemSecretTokenClaims(
                secret="raw-secret",
                token_type="item_secret",
                iat=1710000000,
                exp=1810000000,
            )
        )

        existing_validation = SimpleNamespace(
            id=9,
            item_id=1,
            rank=3,
            created_at="2026-06-29T06:00:00Z",
        )
        item_service = MagicMock()
        item_service.get_active_catalog_item = AsyncMock(
            return_value=build_catalog_row()
        )
        item_service.get_active_item_for_update = AsyncMock(
            return_value=build_catalog_row()[0]
        )
        validation_service = MagicMock()
        validation_service.get_user_item_validation = AsyncMock(
            return_value=existing_validation
        )
        validation_service.create_validation = AsyncMock()
        item_secret_service = MagicMock()
        item_secret_service.hash_secret.return_value = "secret-hash"
        item_secret_service.get_active_by_secret_hash = AsyncMock(
            return_value=SimpleNamespace(id=5, item_id=1)
        )
        service.item_service = item_service
        service.validation_service = validation_service
        service.item_secret_service = item_secret_service
        with (
            patch("app.services.business.items.ItemService", return_value=item_service),
            patch(
                "app.services.business.items.ValidationService",
                return_value=validation_service,
            ),
            patch(
                "app.services.business.items.ItemSecretService",
                return_value=item_secret_service,
            ),
            patch("app.services.business.items.UserService", return_value=user_service),
            patch("app.services.business.items.redis_fail_open", new_callable=AsyncMock) as redis_fail_open_mock,
        ):
            result = await ItemsBusinessService.collect_item_by_secret(
                service,
                SimpleNamespace(id=77),
                SecretValidationRequest(token=token),
            )

        self.assertEqual(result.status, "already_collected")
        self.assertEqual(redis_fail_open_mock.await_count, 0)
        self.assertEqual(validation_service.create_validation.await_count, 0)


class ItemsSecretTokenTests(IsolatedAsyncioTestCase):
    async def test_base64_wrapped_secret_token_is_accepted(self) -> None:
        now = int(time.time())
        token = jwt.encode(
            {
                "secret": "raw-secret",
                "token_type": "item_secret",
                "iat": now,
                "exp": now + 3600,
            },
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        wrapped_token = base64.urlsafe_b64encode(token.encode("utf-8")).decode("utf-8")
        wrapped_token = wrapped_token.rstrip("=")
        service = object.__new__(ItemsBusinessService)

        claims = ItemsBusinessService._decode_item_secret_token(service, wrapped_token)

        self.assertEqual(claims.secret, "raw-secret")

    async def test_invalid_secret_type_is_reported(self) -> None:
        now = int(time.time())
        token = jwt.encode(
            {
                "secret": "raw-secret",
                "token_type": "refresh",
                "iat": now,
                "exp": now + 3600,
            },
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        service = object.__new__(ItemsBusinessService)

        with self.assertRaises(InvalidSecretTypeError):
            ItemsBusinessService._decode_item_secret_token(service, token)

    async def test_missing_secret_is_reported(self) -> None:
        now = int(time.time())
        token = jwt.encode(
            {
                "token_type": "item_secret",
                "iat": now,
                "exp": now + 3600,
            },
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        service = object.__new__(ItemsBusinessService)

        with self.assertRaises(MissingSecretError):
            ItemsBusinessService._decode_item_secret_token(service, token)
