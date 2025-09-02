from celery import Celery

celery_app = Celery(
    "pragyan",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

celery_app.conf.timezone = "Asia/Kolkata"
