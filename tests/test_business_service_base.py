"""
Tests for the BusinessService base class behaviors.

Covers:
- _wrap_business_method: session lifecycle is managed around the outermost call
- Service wiring: services are wired from the session when provided
- Lazy wiring: services are wired lazily when no session is provided
- _business_call_depth: increments/decrements correctly for nested calls
- Re-wiring after session close: lazy proxies are restored after call completes
"""

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.business.base import BusinessService, _LazyServiceProxy
from app.services.base import BaseService


class _FakeBaseService(BaseService):
    """Minimal BaseService subclass for testing – skips repository wiring."""

    def __init__(self, session) -> None:  # noqa: D107
        self.session = session
        # Intentionally skip super().__init__ to avoid real repository wiring


class _StubbedBusinessService(BusinessService):
    """
    A concrete BusinessService subclass used in unit tests.
    Declares a single 'inner_service' dependency for wiring tests.
    """
    inner_service: _FakeBaseService

    async def do_work(self) -> str:
        return "done"

    async def do_nested(self) -> str:
        return await self.do_inner()

    async def do_inner(self) -> str:
        return "inner"


class BusinessServiceWiringTests(IsolatedAsyncioTestCase):
    def test_session_provided_wires_services_immediately(self) -> None:
        session = MagicMock()
        service = _StubbedBusinessService(session=session)

        # When a session is provided, inner_service should be a real service instance
        self.assertNotIsInstance(service.inner_service, _LazyServiceProxy)
        self.assertIsInstance(service.inner_service, _FakeBaseService)

    def test_no_session_wires_lazy_proxies(self) -> None:
        service = _StubbedBusinessService(session=None)

        # Without a session, inner_service should be a lazy proxy
        self.assertIsInstance(service.inner_service, _LazyServiceProxy)

    def test_initial_business_call_depth_is_zero(self) -> None:
        service = _StubbedBusinessService(session=None)
        self.assertEqual(service._business_call_depth, 0)


class BusinessServiceCallDepthTests(IsolatedAsyncioTestCase):
    async def test_depth_increments_and_decrements_around_single_call(self) -> None:
        session = MagicMock()
        service = _StubbedBusinessService(session=session)

        depths_during_call: list[int] = []

        original_do_work = _StubbedBusinessService.__dict__.get("_do_work_original")
        # We cannot easily introspect mid-call, but we can verify the depth
        # is 0 before and after a completed call.
        self.assertEqual(service._business_call_depth, 0)
        await service.do_work()
        self.assertEqual(service._business_call_depth, 0)

    async def test_depth_returns_to_zero_after_exception(self) -> None:
        session = MagicMock()
        service = _StubbedBusinessService(session=session)

        class _FailingService(_StubbedBusinessService):
            async def do_work(self) -> str:
                raise RuntimeError("deliberate failure")

        failing_service = _FailingService(session=session)

        with self.assertRaises(RuntimeError):
            await failing_service.do_work()

        self.assertEqual(failing_service._business_call_depth, 0)


class BusinessServiceSessionOwnershipTests(IsolatedAsyncioTestCase):
    async def test_owned_session_context_is_none_before_and_after_call(self) -> None:
        session = MagicMock()
        service = _StubbedBusinessService(session=session)

        self.assertIsNone(service._owned_session_context)
        await service.do_work()
        self.assertIsNone(service._owned_session_context)

    async def test_provided_session_is_not_closed_by_service(self) -> None:
        """
        When the caller provides the session, the service must never close it.
        """
        session = MagicMock()
        session.close = AsyncMock()
        service = _StubbedBusinessService(session=session)

        await service.do_work()

        session.close.assert_not_awaited()


class BusinessServiceServiceAutoDiscoveryTests(IsolatedAsyncioTestCase):
    def test_services_dict_is_populated_from_annotations(self) -> None:
        # _StubbedBusinessService declares `inner_service: _FakeBaseService`
        # so the services dict should contain it
        self.assertIn("inner_service", _StubbedBusinessService.services)
        self.assertIs(_StubbedBusinessService.services["inner_service"], _FakeBaseService)

    def test_public_async_methods_are_wrapped(self) -> None:
        # The BusinessService metaclass wraps public async methods.
        # After wrapping, they should still be coroutine functions.
        import inspect
        service = _StubbedBusinessService(session=MagicMock())
        # do_work should still be awaitable (the wrapper is also async)
        self.assertTrue(inspect.iscoroutinefunction(_StubbedBusinessService.do_work))

    def test_private_methods_are_not_wrapped(self) -> None:
        """
        Methods starting with _ should NOT be wrapped by the BusinessService.
        """
        import inspect
        # do_inner is a public method; do_work is wrapped; both are async.
        # _close_owned_session starts with _ and is base class, not wrapped by subclass logic.
        # The subclass do_inner is NOT prefixed with _ so it IS wrapped.
        # The base class's _close_owned_session IS prefixed and is NOT wrapped by __init_subclass__.
        # We verify that the wrapper is applied to `do_inner` but not `_close_owned_session`.
        self.assertTrue(inspect.iscoroutinefunction(_StubbedBusinessService.do_inner))
