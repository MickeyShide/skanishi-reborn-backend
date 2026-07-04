from typing import Annotated
from unittest import TestCase

from fastapi import Body
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.main import create_app


class ProbePayload(BaseModel):
    value: int


def create_probe_client() -> TestClient:
    app = create_app()

    @app.post("/_probe/validation")
    async def probe_validation(
        payload: Annotated[ProbePayload, Body()],
    ) -> ProbePayload:
        return payload

    @app.get("/_probe/unhandled")
    async def probe_unhandled() -> None:
        raise RuntimeError("boom")

    return TestClient(app, raise_server_exceptions=False)


def assert_error_response_has_request_id(test_case: TestCase, response) -> None:
    body = response.json()
    request_id = response.headers["X-Request-ID"]

    test_case.assertEqual(set(body), {"error"})
    test_case.assertEqual(body["error"]["request_id"], request_id)
    test_case.assertTrue(body["error"]["code"])
    test_case.assertTrue(body["error"]["message"])


class ErrorHandlerTests(TestCase):
    def test_http_errors_use_common_format_with_request_id(self) -> None:
        response = create_probe_client().get(
            "/_probe/missing",
            headers={"X-Request-ID": "test-http-error"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")
        assert_error_response_has_request_id(self, response)

    def test_validation_errors_use_common_format_with_request_id(self) -> None:
        response = create_probe_client().post(
            "/_probe/validation",
            json={"value": "bad"},
            headers={"X-Request-ID": "test-validation-error"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "validation_error")
        assert_error_response_has_request_id(self, response)

    def test_unhandled_errors_use_common_format_with_request_id(self) -> None:
        response = create_probe_client().get(
            "/_probe/unhandled",
            headers={"X-Request-ID": "test-unhandled-error"},
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "internal_error")
        assert_error_response_has_request_id(self, response)
