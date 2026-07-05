from __future__ import annotations

import base64
import binascii
from typing import Any

import jwt
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.redis_client import redis_client, redis_fail_open
from app.db.models.user import User, UserRole
from app.db.models.validation import Validation
from app.db.repositories.errors import ObjectNotFoundError
from app.db.repositories.item import ItemCatalogRow
from app.schemas.common import ItemRatingQueryParams, ItemsCatalogQueryParams, PageMeta
from app.schemas.item import (
    CategoryResponse,
    ItemFullResponse,
    ItemHiddenResponse,
    ItemResponse,
    ItemsResponse,
    MyItemsResponse,
    PrototypeResponse,
)
from app.schemas.item_type import ItemTypeResponse
from app.schemas.user import UserPublic
from app.schemas.validation import (
    ItemRatingResponse,
    ItemSecretTokenClaims,
    RatingEntryResponse,
    SecretValidationRequest,
    ValidationResponse,
    ValidationShortResponse,
)
from app.services.business.base import BusinessService
from app.services.errors import (
    InvalidAccessTokenError,
    InvalidSecretTokenError,
    InvalidSecretTypeError,
    ItemNotCollectedError,
    ItemNotFoundError,
    MissingSecretError,
    SecretNotFoundError,
    UserNotFoundError,
    ValidationConflictError,
)
from app.services.item import ItemService
from app.services.item_secret import ItemSecretService
from app.services.user import UserService
from app.services.validation import ValidationService


class ItemsBusinessService(BusinessService):
    item_service: ItemService
    validation_service: ValidationService
    item_secret_service: ItemSecretService

    def __init__(
        self,
        session: AsyncSession | None = None,
    ) -> None:
        super().__init__(session=session)

    async def get_items(self, current_user: User, params: ItemsCatalogQueryParams) -> ItemsResponse:

        rows = await self.item_service.get_active_catalog_page(
            limit=params.limit,
            offset=params.offset,
            category_id=params.category_id,
            type_id=params.type_id,
        )
        total = await self.item_service.count_active_catalog(
            category_id=params.category_id,
            type_id=params.type_id,
        )

        return ItemsResponse(
            items=[self._build_full_item_response(row) for row in rows],
            meta=self._build_page_meta(
                limit=params.limit,
                offset=params.offset,
                total=total,
            ),
        )

    async def get_my_items(self, current_user: User, params: ItemsCatalogQueryParams) -> MyItemsResponse:

        rows = await self.item_service.get_active_catalog_page(
            limit=params.limit,
            offset=params.offset,
            category_id=params.category_id,
            type_id=params.type_id,
        )
        total = await self.item_service.count_active_catalog(
            category_id=params.category_id,
            type_id=params.type_id,
        )
        item_ids = [item.id for item, *_ in rows]
        collected_item_ids = await self.validation_service.get_user_item_ids(
            user_id=current_user.id,
            item_ids=item_ids,
        )

        return MyItemsResponse(
            items=[
                self._build_item_response(
                    row,
                    collected=row[0].id in collected_item_ids,
                )
                for row in rows
            ],
            meta=self._build_page_meta(
                limit=params.limit,
                offset=params.offset,
                total=total,
            ),
        )

    async def get_item(self, current_user: User, item_id: int) -> ItemResponse:
        row = await self._get_catalog_item_or_raise(item_id)
        validation = await self.validation_service.get_user_item_validation(
            user_id=current_user.id,
            item_id=item_id,
        )

        return self._build_item_response(row, collected=validation is not None)

    async def get_full_item(self, current_user: User, item_id: int) -> ItemFullResponse:
        row = await self._get_catalog_item_or_raise(item_id)

        if not self._is_privileged(current_user):
            validation = await self.validation_service.get_user_item_validation(
                user_id=current_user.id,
                item_id=item_id,
            )
            if validation is None:
                raise ItemNotCollectedError()

        return self._build_full_item_response(row)

    async def get_item_rating(
        self,
        current_user: User,
        item_id: int,
        params: ItemRatingQueryParams,
    ) -> ItemRatingResponse:

        item = await self.item_service.get_active_item_by_id(item_id)
        if item is None:
            raise ItemNotFoundError()

        rows = await self.validation_service.get_item_rating_page(
            item_id=item_id,
            limit=params.limit,
            offset=params.offset,
        )
        total = await self.validation_service.count_item_rating(item_id=item_id)

        return ItemRatingResponse(
            items=[
                self._build_rating_entry_response(validation, user)
                for validation, user in rows
            ],
            meta=self._build_page_meta(
                limit=params.limit,
                offset=params.offset,
                total=total,
            ),
        )

    async def collect_item_by_secret(
        self,
        current_user: User,
        dto: SecretValidationRequest,
    ) -> ValidationResponse:
        claims = self._decode_item_secret_token(dto.token)

        item_secret = await self.item_secret_service.get_active_by_secret_hash(
            self.item_secret_service.hash_secret(claims.secret)
        )
        if item_secret is None:
            raise SecretNotFoundError()

        catalog_row = await self.item_service.get_active_catalog_item(
            item_secret.item_id
        )
        if catalog_row is None:
            raise SecretNotFoundError()

        item = await self.item_service.get_active_item_for_update(item_secret.item_id)
        if item is None:
            raise SecretNotFoundError()

        existing_validation = await self.validation_service.get_user_item_validation(
            user_id=current_user.id,
            item_id=item.id,
        )
        item_response = self._build_full_item_response(catalog_row)

        if existing_validation is not None:
            return ValidationResponse(
                status="already_collected",
                validation=self._build_validation_short_response(
                    existing_validation
                ),
                item=item_response,
            )

        rank = item.validation_count + 1

        await self.item_service.increment_validation_count(item)

        try:
            validation = await self.validation_service.create_validation(
                user_id=current_user.id,
                item_id=item.id,
                item_secret_id=item_secret.id,
                rank=rank,
            )
        except IntegrityError as exc:
            raise ValidationConflictError() from exc

        await redis_fail_open(
            lambda: redis_client.delete(f"user:{current_user.id}:validation_count"),
            default=0,
        )

        return ValidationResponse(
            status="created",
            validation=self._build_validation_short_response(validation),
            item=item_response,
        )

    async def _get_catalog_item_or_raise(self, item_id: int) -> ItemCatalogRow:
        row = await self.item_service.get_active_catalog_item(item_id)
        if row is None:
            raise ItemNotFoundError()

        return row




    def _decode_item_secret_token(self, raw_token: str) -> ItemSecretTokenClaims:
        for candidate in self._get_secret_token_candidates(raw_token):
            try:
                payload = jwt.decode(
                    candidate,
                    settings.SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM],
                )
            except jwt.ExpiredSignatureError as exc:
                raise InvalidSecretTokenError() from exc
            except jwt.InvalidTokenError:
                continue

            token_type = payload.get("token_type")
            if token_type != "item_secret":
                raise InvalidSecretTypeError()

            secret = payload.get("secret")
            if not isinstance(secret, str) or not secret.strip():
                raise MissingSecretError()

            try:
                return ItemSecretTokenClaims.model_validate(payload)
            except ValidationError as exc:
                raise InvalidSecretTokenError() from exc

        raise InvalidSecretTokenError()

    def _get_secret_token_candidates(self, raw_token: str) -> list[str]:
        candidates = [raw_token]
        decoded = self._decode_base64url(raw_token)
        if decoded is not None and decoded not in candidates:
            candidates.append(decoded)

        return candidates

    @staticmethod
    def _decode_base64url(value: str) -> str | None:
        padding = "=" * (-len(value) % 4)

        try:
            decoded = base64.urlsafe_b64decode((value + padding).encode("utf-8"))
        except (ValueError, binascii.Error):
            return None

        try:
            return decoded.decode("utf-8")
        except UnicodeDecodeError:
            return None

    @staticmethod
    def _is_privileged(user: User) -> bool:
        return user.role in {UserRole.MOD, UserRole.ADMIN}

    @staticmethod
    def _build_page_meta(*, limit: int, offset: int, total: int) -> PageMeta:
        return PageMeta(limit=limit, offset=offset, total=total)

    def _build_item_response(
        self,
        row: ItemCatalogRow,
        *,
        collected: bool,
    ) -> ItemResponse:
        if collected:
            return self._build_full_item_response(row)

        item, category, prototype, item_type = row
        return ItemHiddenResponse(
            id=item.id,
            title=None,
            number=None,
            type=self._build_item_type_response(item_type),
            category=self._build_category_response(category),
            prototype=self._build_prototype_response(prototype),
        )

    def _build_full_item_response(self, row: ItemCatalogRow) -> ItemFullResponse:
        item, category, prototype, item_type = row
        return ItemFullResponse(
            id=item.id,
            title=item.title,
            number=item.number,
            type=self._build_item_type_response(item_type),
            category=self._build_category_response(category),
            prototype=self._build_prototype_response(prototype),
        )

    @staticmethod
    def _build_item_type_response(item_type: Any) -> ItemTypeResponse:
        return ItemTypeResponse(
            id=item_type.id,
            title=item_type.title,
            description=item_type.description,
            photo_url=item_type.photo_url,
        )

    @staticmethod
    def _build_category_response(category: Any) -> CategoryResponse:
        return CategoryResponse(
            id=category.id,
            title=category.title,
            color=category.color,
            description=category.description,
        )

    @staticmethod
    def _build_prototype_response(prototype: Any) -> PrototypeResponse:
        return PrototypeResponse(
            id=prototype.id,
            title=prototype.title,
            description=prototype.description,
            photo_url=prototype.photo_url,
            type_id=prototype.type_id,
        )

    @staticmethod
    def _build_rating_entry_response(
        validation: Validation,
        user: User,
    ) -> RatingEntryResponse:
        return RatingEntryResponse(
            rank=validation.rank,
            created_at=validation.created_at,
            user=(None if user.is_private else UserPublic.model_validate(user)),
        )

    @staticmethod
    def _build_validation_short_response(
        validation: Validation,
    ) -> ValidationShortResponse:
        return ValidationShortResponse(
            id=validation.id,
            item_id=validation.item_id,
            rank=validation.rank,
            created_at=validation.created_at,
        )
