# app/business/base.py

from __future__ import annotations
from __future__ import annotations

from typing import ClassVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.base import BaseService


class BusinessService:
    """
    Базовый класс бизнес-сценариев.

    Один публичный метод дочернего класса = один законченный бизнес-сценарий.
    """

    services: ClassVar[dict[str, type[BaseService]]] = {}

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._wire_services()

    def _wire_services(self) -> None:
        for attr_name, service_cls in self.services.items():
            setattr(self, attr_name, service_cls(self.session))
