from app.workers.tasks import process_scan_claimed

class EventDispatcher:
    def emit(self, event_name: str, payload: dict):
        if event_name == "scan_claimed":
            # Вызываем асинхронную задачу Celery для начисления опыта и левелапа
            process_scan_claimed.delay(payload)

event_dispatcher = EventDispatcher()
