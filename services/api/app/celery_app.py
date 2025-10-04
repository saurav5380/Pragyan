from celery import Celery
from datetime import timedelta
# from celery.schedules import crontab

celery_app = Celery(
    "pragyan",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

celery_app.conf.timezone = "Asia/Kolkata"

celery_app.conf.beat_schedule = {
        "trade_pipeline": {
            "task" : "app.workers.tasks.run_trade_pipeline",
            "schedule" : timedelta(minutes=5),
            'args': (),
            'options': {'queue': 'intraday'}, 
        }
}

