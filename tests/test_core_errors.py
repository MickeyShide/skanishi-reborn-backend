from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic_core import InitErrorDetails

from app.core.errors import register_error_handlers
from app.services.errors import AppServiceError

# Create a dummy app to mount error handlers
app = FastAPI()
register_error_handlers(app)

@app.get("/test-validation-error")
def trigger_validation_error():
    # Simulate FastAPI raising a RequestValidationError
    raise RequestValidationError(errors=[
        InitErrorDetails(type="missing", loc=("query", "id"), input=None)
    ])

@app.get("/test-http-exception")
def trigger_http_exception():
    raise HTTPException(status_code=403, detail="Custom Forbidden Message")

@app.get("/test-http-exception-dict")
def trigger_http_exception_dict():
    raise HTTPException(status_code=400, detail={"code": "custom_code", "message": "Custom Msg"})

@app.get("/test-app-service-error")
def trigger_app_service_error():
    raise AppServiceError(code="domain_error", message="Domain constraint failed", status_code=409)

@app.get("/test-unhandled-exception")
def trigger_unhandled_exception():
    raise ValueError("Something exploded!")

client = TestClient(app, raise_server_exceptions=False)

class TestCoreErrors:
    def test_validation_exception_handler(self) -> None:
        response = client.get("/test-validation-error")
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "validation_error"
        assert "details" in data["error"]

    def test_http_exception_handler_string_detail(self) -> None:
        response = client.get("/test-http-exception")
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "forbidden"
        assert data["error"]["message"] == "Custom Forbidden Message"

    def test_http_exception_handler_dict_detail(self) -> None:
        response = client.get("/test-http-exception-dict")
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "custom_code"
        assert data["error"]["message"] == "Custom Msg"

    def test_app_service_exception_handler(self) -> None:
        response = client.get("/test-app-service-error")
        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "domain_error"
        assert data["error"]["message"] == "Domain constraint failed"

    def test_universal_exception_handler(self) -> None:
        response = client.get("/test-unhandled-exception")
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "internal_error"
        assert data["error"]["message"] == "Internal server error."
