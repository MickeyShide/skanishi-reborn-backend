from celery import Celery
from app.config import settings

from kombu import Queue, Exchange

celery_app = Celery(
    "skanishi_worker",
    broker=settings.CELERY_BROKER_URL,
    include=["app.workers.tasks", "app.workers.outbox", "app.workers.game_tasks", "app.workers.season_tasks"]
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
    # Core outbox relay — keeps latency low
    "publish-outbox-every-2-seconds": {
        "task": "app.workers.outbox.publish_outbox_events",
        "schedule": 2.0,
    },
    # Streak maintenance: reset users who haven't logged in for 25h
    "reset-expired-streaks-hourly": {
        "task": "app.workers.tasks.reset_expired_streaks",
        "schedule": 3600.0,  # every hour
    },
    # Leaderboard: recompute user ranks
    "update-rankings-every-5-minutes": {
        "task": "app.workers.tasks.update_rankings",
        "schedule": 300.0,  # every 5 minutes
    },
    # Housekeeping: delete old ProcessedEvent rows
    "cleanup-processed-events-daily": {
        "task": "app.workers.tasks.cleanup_processed_events",
        "schedule": 86400.0,  # every 24 hours
    },
    # Housekeeping: delete expired RefreshSession rows
    "cleanup-refresh-sessions-daily": {
        "task": "app.workers.tasks.cleanup_refresh_sessions",
        "schedule": 86400.0,  # every 24 hours
    },
    # Seasons: check for expired active season
    "close-active-season-hourly": {
        "task": "app.workers.season_tasks.close_active_season",
        "schedule": 3600.0,  # every hour
    },
}
