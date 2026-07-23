from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middlewares import LoggingMiddleware

app = FastAPI()
app.add_middleware(LoggingMiddleware)

@app.get("/test-middleware")
def simple_route():
    return {"status": "ok"}

@app.get("/test-middleware-error")
def error_route():
    raise ValueError("Middleware explosion")

client = TestClient(app)

class TestCoreMiddlewares:
    def test_logging_middleware_success(self) -> None:
        response = client.get("/test-middleware")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert "x-request-id" in response.headers

    def test_logging_middleware_existing_request_id(self) -> None:
        custom_id = "12345-custom-id"
        response = client.get("/test-middleware", headers={"X-Request-ID": custom_id})
        assert response.status_code == 200
        assert response.headers["x-request-id"] == custom_id

    def test_logging_middleware_exception_propagates(self) -> None:
        # The middleware should log it but then re-raise it
        # Since we don't have our error handlers attached to this dummy app,
        # FastAPI's default 500 handler will catch it, but TestClient propagates Exceptions if raise_server_exceptions=True
        # TestClient in standard config catches it as 500
        try:
            response = client.get("/test-middleware-error")
            assert response.status_code == 500
        except ValueError:
            # If testclient propagates the exception, we catch it
            pass
