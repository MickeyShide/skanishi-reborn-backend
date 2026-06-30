from __future__ import annotations

from abc import ABC
from typing import Any, Generic, TypeVar, ClassVar

from sqlalchemy import Select, select
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.base import BaseSQLModel
from app.db.repositories.errors import ObjectNotFoundError, MultipleObjectsFoundError

T = TypeVar("T", bound=BaseSQLModel)


class BaseRepository(Generic[T], ABC):
    model: ClassVar[type[T]]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _base_query(self) -> Select[tuple[T]]:
        return select(self.model)

    @classmethod
    def _apply_filters(
        cls,
        query: Select[tuple[T]],
        filters: dict[str, Any],
    ) -> Select[tuple[T]]:
        if not filters:
            return query

        return query.filter_by(**filters)

    async def create(self, **data: Any) -> T:
        obj = self.model(**data)

        self.session.add(obj)

        # flush отправляет INSERT в БД, но НЕ делает commit
        await self.session.flush()

        # refresh нужен, чтобы получить id/default/server_default
        await self.session.refresh(obj)

        return obj

    async def get_by_id(self, object_id: int) -> T:
        obj = await self.session.get(self.model, object_id)

        if obj is None:
            raise ObjectNotFoundError(
                f"{self.model.__name__} with id={object_id} was not found"
            )

        return obj

    async def get_one(self, **filters: Any) -> T:
        query = self._apply_filters(self._base_query(), filters)

        result = await self.session.execute(query)

        try:
            obj = result.scalar_one_or_none()
        except MultipleResultsFound as exc:
            raise MultipleObjectsFoundError(
                f"Expected one {self.model.__name__}, got multiple"
            ) from exc

        if obj is None:
            raise ObjectNotFoundError(
                f"{self.model.__name__} was not found by filters={filters}"
            )

        return obj

    async def get_one_or_none(self, **filters: Any) -> T | None:
        query = self._apply_filters(self._base_query(), filters)

        result = await self.session.execute(query)

        try:
            return result.scalar_one_or_none()
        except MultipleResultsFound as exc:
            raise MultipleObjectsFoundError(
                f"Expected one {self.model.__name__}, got multiple"
            ) from exc

    async def get_first(self, **filters: Any) -> T | None:
        query = self._apply_filters(self._base_query(), filters)

        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_all(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        **filters: Any,
    ) -> list[T]:
        query = self._apply_filters(self._base_query(), filters)

        if offset is not None:
            query = query.offset(offset)

        if limit is not None:
            query = query.limit(limit)

        result = await self.session.execute(query)

        return list(result.scalars().all())

    async def exists(self, **filters: Any) -> bool:
        query = self._apply_filters(select(self.model.id), filters).limit(1)

        result = await self.session.execute(query)

        return result.scalar_one_or_none() is not None

    async def update(self, obj: T, **data: Any) -> T:
        for field, value in data.items():
            setattr(obj, field, value)

        await self.session.flush()
        await self.session.refresh(obj)

        return obj

    async def update_by_id(self, object_id: int, **data: Any) -> T:
        obj = await self.get_by_id(object_id)
        return await self.update(obj, **data)

    async def delete(self, obj: T) -> None:
        await self.session.delete(obj)
        await self.session.flush()

    async def delete_by_id(self, object_id: int) -> None:
        obj = await self.get_by_id(object_id)
        await self.delete(obj)
