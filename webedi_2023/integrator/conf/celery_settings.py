import os

celery_url = os.environ.get("REDIS_PLATEIQ_CELERY_URL", "redis://localhost:6379/")
BROKER_URL = celery_url
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_ACKS_LATE = True
CELERY_ENABLE_REMOTE_CONTROL = False

# Default timeouts. If any task is expected to take longer, force them to specify so in the @task decorator
CELERY_TASK_SOFT_TIME_LIMIT = int(os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", 5 * 60))
CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", 10 * 60))

if os.environ.get("CELERYD_MAX_TASKS_PER_CHILD", None):
    CELERYD_MAX_TASKS_PER_CHILD = int(os.environ.get("CELERYD_MAX_TASKS_PER_CHILD"))
