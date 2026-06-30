import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logger import request_id_ctx
from app.schemas.common import ErrorDetail, ErrorResponse
from app.services.errors import AppServiceError

logger = logging.getLogger("app")


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
                code="VALIDATION_ERROR",
                message="Введенные данные не прошли валидацию.",
                details=exc.errors(),  # Массив с указанием loc, msg, type от Pydantic
                request_id=req_id,
            )
        )
        return _error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, payload)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """
        Обработчик явных HTTPException, которые мы бросаем внутри сервисов/роутов
        (например, raise HTTPException(status_code=401, detail="Invalid token")).
        """
        req_id = _get_request_id(request)

        # ТЗ требует разделять причины JWT errors и возвращать 400 вместо 500
        # Если деталь ошибки передана как словарь или строка, мы упакуем ее красиво
        code = f"HTTP_{exc.status_code}_ERROR"
        details = None
        if isinstance(exc.detail, (dict, list)):
            if isinstance(exc.detail, dict):
                code = exc.detail.get("code", code)
                message = exc.detail.get(
                    "message",
                    "Произошла ошибка при обработке запроса.",
                )
                details = exc.detail.get("details", exc.detail)
            else:
                details = exc.detail
                message = "Произошла ошибка при обработке запроса."
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
                code="INTERNAL_SERVER_ERROR",
                message="Внутренняя ошибка сервера. Мы уже работаем над исправлением.",
                request_id=req_id,
            )
        )
        return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, payload)
