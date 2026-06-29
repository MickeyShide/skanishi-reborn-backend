import logging
import sys
from contextvars import ContextVar

# Контекстная переменная для хранения Request ID в рамках одного запроса
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """
    Фильтр, который динамически добавляет request_id в каждую запись лога.
    Если мы логируем вне контекста запроса, будет выведено "NOT_SET".
    """

    def filter(self, record):
        record.request_id = request_id_ctx.get() or "NOT_SET"
        return True


def setup_logging(log_level: str = "INFO"):
    # Настройка базового логгера
    _logger = logging.getLogger("app")
    _logger.setLevel(log_level)

    # Формат лога: Время [Уровень] [Request_ID] (Файл:Линия) - Сообщение
    log_format = logging.Formatter(
        fmt=(
            "%(asctime)s [%(levelname)s] [%(request_id)s] "
            "(%(filename)s:%(lineno)d) - %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Вывод в консоль (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)

    # Подключаем наш фильтр к хэндлеру
    console_handler.addFilter(RequestIdFilter())

    # Очищаем старые хэндлеры, если они были, и добавляем новый
    _logger.handlers = []
    _logger.addHandler(console_handler)

    # Отключаем дублирование логов в корневой логгер
    _logger.propagate = False


# Создаем экземпляр логгера для импорта в другие файлы
logger = logging.getLogger("app")
