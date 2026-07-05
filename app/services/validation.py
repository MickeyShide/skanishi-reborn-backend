from app.db.models.validation import Validation
from app.db.repositories.validation import ItemRatingRow, ValidationRepository
from app.services.base import BaseService


class ValidationService(BaseService):
    repositories = {
        "validation_repository": ValidationRepository,
    }

    validation_repository: ValidationRepository

    async def get_user_item_ids(
        self,
        *,
        user_id: int,
        item_ids: list[int],
    ) -> set[int]:
        return await self.validation_repository.get_user_item_ids(
            user_id=user_id,
            item_ids=item_ids,
        )

    async def get_user_item_validation(
        self,
        *,
        user_id: int,
        item_id: int,
    ) -> Validation | None:
        return await self.validation_repository.get_user_item_validation(
            user_id=user_id,
            item_id=item_id,
        )

    async def get_item_rating_page(
        self,
        *,
        item_id: int,
        limit: int,
        offset: int,
    ) -> list[ItemRatingRow]:
        return await self.validation_repository.get_item_rating_page(
            item_id=item_id,
            limit=limit,
            offset=offset,
        )

    async def count_item_rating(self, *, item_id: int) -> int:
        return await self.validation_repository.count_item_rating(item_id=item_id)

    async def count_user_validations(self, *, user_id: int) -> int:
        return await self.validation_repository.count_user_validations(user_id=user_id)

    async def create_validation(
        self,
        *,
        user_id: int,
        item_id: int,
        item_secret_id: int,
        rank: int,
    ) -> Validation:
        return await self.validation_repository.create(
            user_id=user_id,
            item_id=item_id,
            item_secret_id=item_secret_id,
            rank=rank,
        )
