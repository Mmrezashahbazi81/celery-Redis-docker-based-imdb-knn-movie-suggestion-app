import os
from celery import Celery

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")   # بیرون Docker → localhost
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "0")

BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
BACKEND_URL = BROKER_URL

def make_celery():
    celery = Celery(
        "imdb_tasks",
        broker=BROKER_URL,
        backend=BACKEND_URL,
    )
    return celery

celery = make_celery()
