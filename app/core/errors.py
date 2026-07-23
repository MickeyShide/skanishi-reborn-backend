import logging
from http import HTTPStatus

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logger import request_id_ctx
from app.schemas.common import ErrorDetail, ErrorResponse
from app.services.errors import AppServiceError

logger = logging.getLogger("app")


HTTP_ERROR_CODES: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "validation_error",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "internal_error",
    status.HTTP_503_SERVICE_UNAVAILABLE: "service_not_ready",
}


def _get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None) or request_id_ctx.get()


def _error_response(status_code: int, payload: ErrorResponse) -> JSONResponse:
    request_id = payload.error.request_id
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(),
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """
        Обработчик ошибок валидации Pydantic (код 422).
        """
        req_id = _get_request_id(request)

        # Логируем факт ошибки валидации, чтобы видеть в консоли некорректный body/query
        logger.warning(
            "Validation error on %s %s | errors: %s",
            request.method,
            request.url.path,
            exc.errors(),
        )

        payload = ErrorResponse(
            error=ErrorDetail(
                code="validation_error",
                message="Request validation failed.",
                details=exc.errors(),  # Массив с указанием loc, msg, type от Pydantic
                request_id=req_id,
            )
        )
        return _error_response(status.HTTP_422_UNPROCESSABLE_CONTENT, payload)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """
        Обработчик HTTP-ошибок фреймворка и явных ошибок уровня роутов.
        """
        req_id = _get_request_id(request)

        code = HTTP_ERROR_CODES.get(exc.status_code, "http_error")
        message = HTTPStatus(exc.status_code).phrase
        details = None

        if isinstance(exc.detail, (dict, list)):
            if isinstance(exc.detail, dict):
                code = exc.detail.get("code", code)
                message = exc.detail.get("message", message)
                details = exc.detail.get("details")
            else:
                details = exc.detail
        else:
            message = str(exc.detail)

        payload = ErrorResponse(
            error=ErrorDetail(
                code=code,
                message=message,
                details=details,
                request_id=req_id,
            )
        )
        return _error_response(exc.status_code, payload)

    @app.exception_handler(AppServiceError)
    async def app_service_exception_handler(request: Request, exc: AppServiceError):
        req_id = _get_request_id(request)

        payload = ErrorResponse(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=req_id,
            )
        )
        return _error_response(exc.status_code, payload)

    @app.exception_handler(Exception)
    async def universal_exception_handler(request: Request, exc: Exception):
        """
        Глобальный перехватчик всех непредвиденных ошибок (код 500).
        Гарантирует, что пользователь никогда не увидит сырой Python Traceback,
        при этом вся ошибка пишется в логи вместе с Request ID.
        """
        req_id = _get_request_id(request)

        # logger.exception автоматически прикрепит весь Traceback к этому логу
        logger.exception(
            f"Unhandled internal server error on {request.method} {request.url.path}"
        )

        payload = ErrorResponse(
            error=ErrorDetail(
                code="internal_error",
                message="Internal server error.",
                request_id=req_id,
            )
        )
        return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, payload)
