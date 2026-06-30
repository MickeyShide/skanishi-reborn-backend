# app/services/base.py

from __future__ import annotations

from typing import Any, ClassVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository


class BaseService:
    """
    Базовый сервис.

    Отвечает за подключение репозиториев к сервису.
    Сам бизнес-сценарии не выполняет.
    """

    repositories: ClassVar[dict[str, type[BaseRepository[Any]]]] = {}

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._wire_repositories()

    def _wire_repositories(self) -> None:
        for attr_name, repository_cls in self.repositories.items():
            setattr(self, attr_name, repository_cls(self.session))
