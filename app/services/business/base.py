from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from types import TracebackType
from typing import Any, ClassVar, TypeVar, get_type_hints

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import session_context
from app.services.base import BaseService

R = TypeVar("R")


class _LazyServiceProxy:
    def __init__(
        self,
        business_service: BusinessService,
        attr_name: str,
        service_cls: type[BaseService],
    ) -> None:
        self._business_service = business_service
        self._attr_name = attr_name
        self._service_cls = service_cls

    def __getattr__(self, method_name: str) -> Any:
        try:
            attr = inspect.getattr_static(self._service_cls, method_name)
            if isinstance(attr, (staticmethod, classmethod)):
                return attr.__get__(None, self._service_cls)
        except AttributeError:
            pass

        async def call(*args: Any, **kwargs: Any) -> Any:
            service = await self._business_service._get_service(
                self._attr_name,
                self._service_cls,
            )
            result = getattr(service, method_name)(*args, **kwargs)
            if inspect.isawaitable(result):
                return await result
            return result

        return call


class BusinessService:
    """
    Базовый класс бизнес-сценариев.

    Один публичный метод дочернего класса = один законченный бизнес-сценарий.
    DB-сессия открывается лениво: при первом обращении к дочернему сервису
    внутри публичного async-метода.
    """

    services: ClassVar[dict[str, type[BaseService]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.services = cls._collect_services()

        for attr_name, attr in cls.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if inspect.iscoroutinefunction(attr):
                setattr(cls, attr_name, cls._wrap_business_method(attr))

    @classmethod
    def _collect_services(cls) -> dict[str, type[BaseService]]:
        services = dict(getattr(cls, "services", {}))

        try:
            annotations = get_type_hints(cls)
        except (NameError, TypeError):
            annotations = cls.__dict__.get("__annotations__", {})

        for attr_name, annotation in annotations.items():
            if inspect.isclass(annotation) and issubclass(annotation, BaseService):
                services[attr_name] = annotation

        return services

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        self._owned_session_context = None
        self._business_call_depth = 0

        if session is None:
            self._wire_lazy_services()
        else:
            self._wire_services()

    @staticmethod
    def _wrap_business_method(
        func: Callable[..., Awaitable[R]],
    ) -> Callable[..., Awaitable[R]]:
        @wraps(func)
        async def wrapper(self: BusinessService, *args: Any, **kwargs: Any) -> R:
            is_outermost_call = getattr(self, "_business_call_depth", 0) == 0
            self._business_call_depth = getattr(self, "_business_call_depth", 0) + 1

            exc_type: type[BaseException] | None = None
            exc: BaseException | None = None
            tb: TracebackType | None = None

            try:
                return await func(self, *args, **kwargs)
            except BaseException as caught:
                exc_type = type(caught)
                exc = caught
                tb = caught.__traceback__
                raise
            finally:
                self._business_call_depth -= 1
                if is_outermost_call:
                    await self._close_owned_session(exc_type, exc, tb)

        return wrapper

    def _wire_services(self) -> None:
        if self.session is None:
            raise RuntimeError("Cannot wire DB services without a session.")

        for attr_name, service_cls in self.services.items():
            setattr(self, attr_name, service_cls(self.session))

    def _wire_lazy_services(self) -> None:
        for attr_name, service_cls in self.services.items():
            setattr(self, attr_name, _LazyServiceProxy(self, attr_name, service_cls))

    async def _get_service(
        self,
        attr_name: str,
        service_cls: type[BaseService],
    ) -> BaseService:
        await self._ensure_session()

        service = getattr(self, attr_name)
        if isinstance(service, _LazyServiceProxy):
            service = service_cls(self.session)
            setattr(self, attr_name, service)

        return service

    async def _ensure_session(self) -> AsyncSession:
        if self.session is not None:
            return self.session

        if getattr(self, "_business_call_depth", 0) == 0:
            raise RuntimeError(
                "Lazy DB services can only be used inside a business method."
            )

        context = session_context()
        try:
            self.session = await context.__aenter__()
        except Exception:
            self.session = None
            raise

        self._owned_session_context = context
        self._wire_services()

        return self.session

    async def _close_owned_session(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        context = getattr(self, "_owned_session_context", None)
        if context is None:
            return

        self._owned_session_context = None
        try:
            await context.__aexit__(exc_type, exc, tb)
        finally:
            self.session = None
            self._wire_lazy_services()
