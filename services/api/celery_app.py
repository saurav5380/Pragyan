from celery import Celery
from datetime import timedelta

celery_app = Celery(
    "pragyan",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

celery_app.conf.timezone = "Asia/Kolkata"

celery_app.conf.beat_schedule = {
        "update-all-stocks-5m": {
            "task" : "app.workers.task.update_all_stocks_5m",
            "schedule" : timedelta(minutes=5)  
        }
}

