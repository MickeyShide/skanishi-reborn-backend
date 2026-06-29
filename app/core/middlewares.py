import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logger import logger, request_id_ctx


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Получаем ID из заголовков или генерируем новый
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # 2. Устанавливаем ID в контекст для логов внутри запроса
        token = request_id_ctx.set(request_id)

        start_time = time.perf_counter()
        logger.info(f"Incoming request: {request.method} {request.url.path}")

        try:
            response: Response = await call_next(request)

            # Добавляем Request ID в заголовки ответа
            response.headers["X-Request-ID"] = request_id

            duration = time.perf_counter() - start_time
            logger.info(
                f"Completed request: {request.method} {request.url.path} "
                f"| Status: {response.status_code} | Duration: {duration:.4f}s"
            )
            return response

        except Exception as exc:
            duration = time.perf_counter() - start_time
            # Здесь логируем ошибку со всем трейсбэком. Благодаря logger.exception
            # в консоли будет видна вся ошибка, привязанная к Request ID!
            logger.exception(
                f"Failed request: {request.method} {request.url.path} "
                f"| Duration: {duration:.4f}s | Error: {str(exc)}"
            )
            raise exc from None

        finally:
            # 3. Сбрасываем контекст после завершения запроса
            request_id_ctx.reset(token)
