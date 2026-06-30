from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import routers
from app.config import settings
from app.core.database import check_database, close_database, init_engine
from app.core.errors import register_error_handlers
from app.core.logger import logger, setup_logging
from app.core.middlewares import LoggingMiddleware
from app.core.redis_client import check_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ==================== STARTUP ====================
    # 1. Сначала настраиваем логирование, чтобы видеть логи инициализации каркаса
    setup_logging(settings.LOG_LEVEL)
    logger.info("Application is starting up (Infrastructure initializing)...")

    init_engine(echo=settings.SQL_ECHO)

    # 2. Проверяем обязательное подключение к PostgreSQL (Принцип Fail-Fast по ТЗ)
    try:
        await check_database()
        logger.info("PostgreSQL connection established successfully.")
    except Exception:
        logger.critical("PostgreSQL startup connection failed", exc_info=True)
        raise

    # 3. Проверяем доступность Redis на старте
    try:
        await check_redis()
        logger.info("Redis connection established successfully.")
    except Exception:
        # Redis работает в fail-open режиме: пишем в лог, но не гасим API.
        logger.warning("Redis is not responding on startup", exc_info=True)

    try:
        # Передаем управление приложению FastAPI для обработки входящих HTTP-запросов
        yield
    finally:
        # ==================== SHUTDOWN ====================
        logger.info("Application is shutting down (Cleaning up resources)...")

        await close_redis()
        await close_database()

        logger.info("Resources cleaned up successfully. Shutdown complete.")


def create_app() -> FastAPI:
    # Инициализируем приложение с поддержкой современного жизненного цикла lifespan
    app = FastAPI(title="Skanishi API", lifespan=lifespan)

    # 1. Добавляем кастомный middleware логирования и Request ID первым,
    # чтобы он замерял время работы последующих middleware
    app.add_middleware(LoggingMiddleware)

    # 2. Настройка CORS из переменных окружения
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.FRONTEND_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Регистрация глобальных обработчиков исключений (Единый формат JSON-ошибок)
    register_error_handlers(app)

    # 4. Подключение всех зарегистрированных роутеров приложения
    for r in routers:
        app.include_router(r)

    return app


# Фабричный запуск инстанса
app: FastAPI = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=4000,
        log_level="info",
        reload=(
            True if settings.APP_ENV == "local" else False
        ),  # Авторелоад только в локальной среде
    )
