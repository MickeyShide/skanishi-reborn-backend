from celery import Celery
from app.config import settings

from kombu import Queue, Exchange

celery_app = Celery(
    "skanishi_worker",
    broker=settings.CELERY_BROKER_URL,
    include=["app.workers.tasks", "app.workers.outbox"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="default",
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue(
            "progress.commands", 
            Exchange("progress.commands"), 
            routing_key="progress.commands",
            queue_arguments={
                "x-dead-letter-exchange": "dlx",
                "x-dead-letter-routing-key": "dead_letters"
            }
        ),
        Queue(
            "notifications.commands", 
            Exchange("notifications.commands"), 
            routing_key="notifications.commands",
            queue_arguments={
                "x-dead-letter-exchange": "dlx",
                "x-dead-letter-routing-key": "dead_letters"
            }
        ),
        Queue("dead_letters", Exchange("dlx"), routing_key="dead_letters"),
    ),
    task_routes={
        "app.workers.tasks.process_scan_claimed": {"queue": "progress.commands"},
        "app.workers.tasks.send_notification": {"queue": "notifications.commands"},
    },
)

celery_app.conf.beat_schedule = {
    "publish-outbox-every-2-seconds": {
        "task": "app.workers.outbox.publish_outbox_events",
        "schedule": 2.0,
    },
}
