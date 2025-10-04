from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

celery_app = Celery(
    "tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
    # This path correctly tells Celery to look in the tasks.py file
    include=['app.tasks'] 
)

celery_app.conf.update(
    task_track_started=True,
)